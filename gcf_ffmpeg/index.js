/*
* ==============================================================================
* Copyright 2018 The Fuego Authors.
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
* ==============================================================================
*/


// Deployment instructions
// gcloud functions deploy fuego-ffmpeg1 --runtime nodejs10 --trigger-http --entry-point=extractMp4 --memory=2048MB --timeout=540s

const os = require('os');
const fs = require('fs');
const path = require('path');
const request = require('request');
const rimraf = require('rimraf');
const google = require('googleapis');
const gDrive = new google.drive_v3.Drive();
const gAuthLib = require("google-auth-library");
const ffmpegPath = require('@ffmpeg-installer/ffmpeg').path;
const FfmpegCommand = require('fluent-ffmpeg');
FfmpegCommand.setFfmpegPath(ffmpegPath);

function getHpwrenUrl(hostName, cameraID, yearDir, dateDir, qNum) {
    var hpwrenUrl = 'http://' + encodeURIComponent(hostName) + '.hpwren.ucsd.edu/archive/';
    hpwrenUrl += encodeURIComponent(cameraID) + '/large/';
    if (yearDir) {
        hpwrenUrl += encodeURIComponent(yearDir) + '/';
    }
    hpwrenUrl += encodeURIComponent(dateDir) + '/MP4/Q' + qNum + '.mp4';
    return hpwrenUrl;
}

function getTmpDir() {
    return fs.mkdtempSync(path.join(os.tmpdir(), 'fuego_ffmpeg_'));
}


function listFiles(dir) {
    files = fs.readdirSync(dir);
    sizes = [];
    files.forEach((file) => {
        ss = fs.statSync(path.join(dir, file));
        sizes.push(ss.size);
    });
    console.log('ListFiles: ', sizes.length, sizes.join(', '));
}

function downloadMp4(mp4Url, mp4File, cb) {
    request(mp4Url,
        function(error, response, body) { // triggers after all the data is received (but before 'complete' event)
            console.log('cb error:', error); // Print the error if one occurred
            console.log('cb statusCode:', response && response.statusCode); // Print the response status code if a response was received
            console.log('cb body', typeof(body), body && body.length); // this length doesn't match file size
        })
        .on('response', function(response) { // triggers on initial response
            console.log('event response sc', response.statusCode) // 200
            console.log('event response ct', response.headers['content-type']) // 'image/png'
        })
        // .on('data', function(data) {  // trigers on every chunk of data received
        //     console.log('event data', typeof(data), data.length); // sum of all data.length matches file size
        // })
        .on('error', function(err) {
            console.log('event error', err);
            cb(err);
        })
        .on('complete', function(resp, body) { // triggers after everything (including cb function to request())
            console.log('event complete sc', typeof(resp), resp.statusCode);
            console.log('event complete body', typeof(body), body.length); // this length doesn't match file size
            cb(null, resp, body);
        })
        .pipe(fs.createWriteStream(mp4File));
}

function getJpegs(mp4File, outFileSpec, cb) {
    var cmd = new FfmpegCommand();
    var cmdLine = null;
    cmd.input(mp4File).output(outFileSpec);
    cmd.format('image2').videoCodec('mjpeg').outputOptions('-qscale 0');
    cmd.on('start',function(cl){console.log('started:' + cl);cmdLine = cl;});
    cmd.on('error',function(err){console.log('errorM:' + err);cb(err)});
    cmd.on('end',function(){console.log('ended!');cb(null, cmdLine)});
    cmd.run();
}

 
function gdriveAuthSericeAccount(keyFile, cb) {
    function authNow(authClient) {
        // When running in google cloud function environment, there is no authorize method
        // and the authClient is ready to use, but when running in framework simulator on
        // local host, authorize() is needed.
        if (!authClient.authorize) {
            cb(null, authClient);
            return;
        }
        authClient.authorize(function (err, tokens) {
            if (err) {
                console.log(err);
                cb(err);
                return;
            } else {
                console.log("Successfully connected!");
                cb(null, authClient);
            }
        });
    }
    const scopes = ['https://www.googleapis.com/auth/drive'];
    var jwtClient;
    if (keyFile) {
        console.log('with key');
        const keyJson = require(keyFile);
        jwtClient = new google.google.auth.JWT(keyJson.client_email, null, keyJson.private_key, scopes);
        authNow(jwtClient);
    } else {
        console.log('app default without key');
        gAuth = new gAuthLib.GoogleAuth({scopes: scopes});
        gAuth.getApplicationDefault(function (err, jwtClient, projectId) {
            if (err) {
                console.log('gad error', err);
                cb(err);
                return;
            } else {
                console.log('get project', projectId);
                authNow(jwtClient);
            }
        });
    }
}

function gdriveAuthToken(credsPath, tokenPath, cb) {
    credsJ = JSON.parse(fs.readFileSync(credsPath));
    tokenJ = JSON.parse(fs.readFileSync(tokenPath));
    oauth2 = new google.google.auth.OAuth2(credsJ.installed.client_id, credsJ.installed.client_secret, credsJ.installed.redirect_uris[0]);
    oauth2.setCredentials({refresh_token: tokenJ.refresh_token});
    cb(null, oauth2);
}

function gdriveList(authClient, parentDir) {
    gDrive.files.list({
        auth: authClient,
        supportsTeamDrives: true,
        includeTeamDriveItems: true,
        q: '"' + parentDir + '" in parents and trashed = False',
    }, function (err, response) {
        if (err) {
            console.log('The API returned an error: ' + err);
            return;
        }
        var files = response.data.files;
        if (files.length == 0) {
            console.log('No files found.');
        } else {
            console.log('Files from Google Drive:');
            for (var i = 0; i < files.length; i++) {
                var file = files[i];
                console.log('%s (%s)', file.name, file.id);
            }
        }
    });
}
function resolveAfter2Seconds(x) { 
    return new Promise(resolve => {
      setTimeout(() => {
        resolve(x);
      }, 2000);
    });
  }
  
  function gdriveUploadCB(authClient, filePath, parentDir) {
    gDrive.files.create({
        auth: authClient,
        resource: {
            'name': path.basename(filePath),
            'parents': [parentDir]
        },
        media: {
            mimeType: 'image/jpeg',
            body: fs.createReadStream(filePath)    
        },
        supportsTeamDrives: true,
        fields: 'id'
    }, function (err, file) {
        if (err) {
            // Handle error
            console.error('Upload error', err);
        } else {
            console.log('File: ', file.status, file.statusText, file.data);
        }
    });
}

function gdriveUploadPromise(authClient, filePath, parentDir, newFileName) {
    return new Promise((resolve,reject) => {
        gDrive.files.create({
            auth: authClient,
            resource: {
                'name': newFileName,
                'parents': [parentDir]
            },
            media: {
                mimeType: 'image/jpeg',
                body: fs.createReadStream(filePath)    
            },
            supportsTeamDrives: true,
            fields: 'id'
        }, function (err, file) {
            if (err) {
                // Handle error
                console.error('Upload error', err);
                reject(err);
            } else {
                // console.log('File: ', file.status, file.statusText, file.data);
                resolve(file);
            }
        });
    });
}

async function gdriveUploadAsync(authClient, filePath, parentDir) {
    try {
        var file = await gdriveUploadPromise(authClient, filePath, parentDir);
        console.log('await file', file.status, file.statusText, file.data);
    } catch (err) {
        console.log('await err', err);
    }
}

function getPaddedMinute(minute) {
    minuteStr = minute.toString()
    if (minute < 10) {
        minuteStr = '0' + minuteStr;
    }
    return minuteStr;
}

async function uploadFiles(fromDir, authClient, uploadDir, driveFilesPrefix, qNum, cb) {
    batchSize = 8; // up to 8 files in parallel gets nice speedup in google cloud environment
    fileNames = fs.readdirSync(fromDir);
    fileNames = fileNames.filter(fn => fn.endsWith('.jpg')); // skip the mp4
    fileNames = fileNames.sort(); // sort by name to ensure correct time ordering
    files = [];
    batchProms = [];
    for (var i = 0; i < fileNames.length; i++) {
        filePath = path.join(fromDir, fileNames[i]);
        hour = (qNum-1)*3 + Math.floor(i/60);
        minute = getPaddedMinute(i % 60);
        newFileName = driveFilesPrefix + hour + ';' + minute + ';00.jpg'
        try {
            batchProms.push(gdriveUploadPromise(authClient, filePath, uploadDir, newFileName));
            if ((batchProms.length >= batchSize) || (i == (fileNames.length - 1))) {
                batchFiles = [];
                for (var j = 0; j < batchProms.length; j++) {
                    fileInfo = await batchProms[j].catch(function(err) {
                        console.log('upload await err', err.message, err);
                    });
                    batchFiles.push(fileInfo);
                }
                batchProms = [];
                files = files.concat(batchFiles);
                console.log('await files', i, batchFiles.map(fi=>fi.status));
            }
        } catch (err) {
            console.log('await err', err);
            cb(err);
            return;
        }
    }
    console.log('finishing upload');
    cb(null, files);
}

/**
 * Responds to any HTTP request.
 *
 * @param {!express:Request} req HTTP request context.
 * @param {!express:Response} res HTTP response context.
 */
exports.extractMp4 = (req, res) => {
    console.log('query', req.query);
    console.log('bodyM', req.body);
    if (!req.body || !req.body.hostName || !req.body.cameraID || !req.body.yearDir || !req.body.dateDir || !req.body.qNum) {
        console.log('Missing parameters');
        res.status(400).send('Missing parameters');
        return;
    }
    var hpwrenUrl = getHpwrenUrl(req.body.hostName, req.body.cameraID, req.body.yearDir, req.body.dateDir, req.body.qNum);
    console.log('URL: ', hpwrenUrl);
    const tmpDir = getTmpDir();
    const mp4File = path.join(tmpDir, 'q.mp4');
    console.log('File: ', mp4File);
    driveFilesPrefix = req.body.cameraID + '__' +
                        req.body.dateDir.slice(0,4) + '-' +
                        req.body.dateDir.slice(4,6) + '-' +
                        req.body.dateDir.slice(6,8) + 'T';
    downloadMp4(hpwrenUrl, mp4File, function(err, resp, body) {
        if (err) {
            res.status(400).send('Could not download mp4');
            return;
        }
        console.log('Listing files after download');
        listFiles(tmpDir);
        const outFileSpec = path.join(tmpDir, 'img-%03d.jpg');
        getJpegs(mp4File, outFileSpec, function (err, cmdLine) {
            if (err) {
                res.status(400).send('Could not decode mp4');
                return;
            }
            console.log('Listing files after ffmpeg');
            listFiles(tmpDir);
            gdriveAuthSericeAccount(null, function(err, authClient) {
                if (err) {
                    res.status(400).send('Could not auth drive');
                    return;
                }
                // console.log('auth done', authClient);
                uploadFiles(tmpDir, authClient, req.body.uploadDir, driveFilesPrefix, req.body.qNum, function(err, files) {
                    if (err) {
                        res.status(400).send('Could not upload jpegs');
                        return;
                    }
                    rimraf.sync(tmpDir);
                    console.log('All done');
                    res.status(200).send('done');
                });
            });
        });
    });
};


function testHandler() {
    exports.extractMp4({ // fake req
        query: {},
        body: {
            hostName: 'c1',
            cameraID: 'rm-w-mobo-c',
            yearDir: 2017,
            dateDir: 20170613,
            qNum: 3, // 'Q3.mp4'
            uploadDir: '1KCdRENKi_b9HgiZ9nzq05P5rTuRH71q2',
        }
    }, { // fake res
        status: () => ({send: (m)=>{console.log('msg', m)}})
    });
}


console.log('argv: ', process.argv)
if ((process.argv.length > 1) && !process.argv[1].includes('functions-framework')) {
    const testDir = '1KCdRENKi_b9HgiZ9nzq05P5rTuRH71q2';
    const TOKEN_PATH = '../../keys/token.json';
    const CREDS_PATH = '../../keys/credentials.json';
    // export GOOGLE_APPLICATION_CREDENTIALS='..../service-account.json'
    const KEY_FILE = '../../keys/service-account.json';
    testHandler();
    // gdriveAuthToken(CREDS_PATH, TOKEN_PATH, function(err, authClient) {
    // gdriveAuthSericeAccount(KEY_FILE, function(err, authClient) {
    // gdriveAuthSericeAccount(null, function(err, authClient) {
        // if (err) {
        //     return;
        // }
        // gdriveList(authClient, testDir);
        // gdriveUploadCB(authClient,
        //     'index.js',
        //     testDir
        // );

        // gdriveUploadPromise(authClient,
        //     'index.js',
        //     testDir
        // ).then(file => {
        //     console.log('prom res', file.status, file.statusText, file.data);
        // }).catch(err => {
        //     console.log('prom rej', err);
        // });

        // gdriveUploadAsync(authClient,
        //     'index.js',
        //     testDir
        // );
    // });
}

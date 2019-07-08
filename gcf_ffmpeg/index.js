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
const os = require('os');
const fs = require('fs');
const path = require('path');
const request = require('request');
const rimraf = require('rimraf');
const ffmpegPath = require('@ffmpeg-installer/ffmpeg').path;
const FfmpegCommand = require('fluent-ffmpeg');
FfmpegCommand.setFfmpegPath(ffmpegPath);

function getHpwrenUrl(hostName, cameraID, yearDir, dateDir, qName) {
    var hpwrenUrl = 'http://' + encodeURIComponent(hostName) + '.hpwren.ucsd.edu/archive/';
    hpwrenUrl += encodeURIComponent(cameraID) + '/large/';
    if (yearDir) {
        hpwrenUrl += encodeURIComponent(yearDir) + '/';
    }
    hpwrenUrl += encodeURIComponent(dateDir) + '/MP4/' + qName;
    return hpwrenUrl;
}

function getTmpDir() {
    return fs.mkdtempSync(path.join(os.tmpdir(), 'fuego_ffmpeg_'));
}


function listFiles(dir) {
    files = fs.readdirSync(dir);
    files.forEach((file) => {
        ss = fs.statSync(path.join(dir, file));
        console.log('LF: ', file, ss.size);
    });
}

function downloadMp4(mp4Url, mp4File, cb) {
    request(mp4Url,
        function(error, response, body) { // triggers after all the data is received (but before 'complete' event)
            console.log('cb error:', error); // Print the error if one occurred
            console.log('cb statusCode:', response && response.statusCode); // Print the response status code if a response was received
            console.log('cb body', typeof(body), body.length); // this length doesn't match file size
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


/**
 * Responds to any HTTP request.
 *
 * @param {!express:Request} req HTTP request context.
 * @param {!express:Response} res HTTP response context.
 */
exports.helloWorld = (req, res) => {
    console.log('query', req.query);
    console.log('bodyM', req.body);
    var hpwrenUrl = getHpwrenUrl(req.body.hostName, req.body.cameraID, req.body.yearDir, req.body.dateDir, req.body.qName);
    console.log('URL: ', hpwrenUrl);
    const tmpDir = getTmpDir();
    const mp4File = path.join(tmpDir, 'q.mp4');
    console.log('File: ', mp4File);
    downloadMp4(hpwrenUrl, mp4File, function(err, resp, body) {
        if (err) {
            return;
        }
        console.log('Listing files after download');
        listFiles(tmpDir);
        const outFileSpec = path.join(tmpDir, 'img-%03d.jpg');
        getJpegs(mp4File, outFileSpec, function (err, cmdLine) {
            console.log('Listing files after ffmpeg');
            listFiles(tmpDir);
        });
        // rimraf.sync(tmpDir);
        // upload to google drive
        console.log('done');
        res.status(200).send('done');
    });
};

console.log('argv: ', process.argv)
if ((process.argv.length > 1) && !process.argv[1].includes('functions-framework')) {
    exports.helloWorld(
        {query:{}, body:{
            hostName: 'c1',
            cameraID: 'rm-w-mobo-c',
            yearDir: 2017,
            dateDir: 20170613,
            qName: 'Q3.mp4'
        }},
        {status: ()=>({send: (m)=>{console.log('msg', m)}})}
    )
}
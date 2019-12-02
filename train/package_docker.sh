#this script packages a trained model into a docker container, and 
#pushes it to the GCR. First arugment should be a name you want to 
#use for the model (i.e. inception), and second argument should be its path

NAME=$1
MODEL_PATH=$2

docker pull tensorflow/serving:latest-gpu
sudo docker run -d --name serving_base tensorflow/serving:latest-gpu
# create intermediate dir
sudo docker exec serving_base mkdir -p /models/$NAME 
sudo docker cp $MODEL_PATH serving_base:/models/$NAME/1
sudo docker commit --change "ENV MODEL_NAME $NAME" serving_base $NAME"_serving"
sudo docker kill serving_base
sudo docker rm serving_base

sudo docker tag $NAME"_serving" gcr.io/dkgu-dev/$NAME"_serving":latest
sudo docker push gcr.io/dkgu-dev/$NAME"_serving":latest

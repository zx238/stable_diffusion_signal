from flask import Flask, request
import subprocess
import json
import uuid
import time
import boto3
import os

app = Flask(__name__)




file_name = 'backend_api_log.txt'

s3_client = boto3.client('s3')
txt2image_s3_bucket = 'stable-diffusion-image'
txt2image_local_path = './outputs/txt2img-samples/samples' 
image2image_local_path = './outputs/img2img-samples/samples' 

def log(*args, **kwargs):
    time_format = '%Y/%m/%d %H:%M:%S'
    localtime = time.localtime(int(time.time()))
    formatted = time.strftime(time_format, localtime)
    with open(file_name, 'a', encoding='utf-8') as f:
        print(formatted, *args, **kwargs)
        print(formatted, *args, file=f, **kwargs)

def run_command(command):
    ret_code, ret_msg = subprocess.getstatusoutput(command)
    log(f'command is:{command}')
    log(ret_code, ret_msg)
    if ret_code != 0:
        return "fail"
    return "success"

def generate_image_name():
    return time.strftime("%Y%m%d-") + str(uuid.uuid4()) + ".png"

def upload_image_to_s3(local_file_path, bucket_name, key_name):
	s3_client.upload_file(local_file_path, bucket_name, key_name)

@app.route('/img2img', methods=['POST'])
def image_to_image():
    body = request.form.to_dict()
    txt = body.get('txt', None)
    log(f'path /img2img received body is:{body}')

    log(f'{request.files}')
    file = request.files.get('file')
    log('keys:', request.files.keys())
    log(f'file:{file}')
    if file is None:
        return json.dumps({'message':'file upload failed'})
    file.save((file.filename))
    log(f'path /img2img received image name is:{file.filename}')
    image_name = generate_image_name()
    status = 'fail'
    image_url = ''
    if txt:
        img_command = f'python scripts/img2img.py --init-img "./{file.filename}" --prompt "{txt}" --strength 0.8 --image_name "{image_name}" --ckpt ./models/sd-v1-4.ckpt'
        log(f'img command is:{img_command}')
        status = run_command(img_command)
        if status == 'success':
            local_file_path = os.path.join(image2image_local_path,image_name)
            upload_image_to_s3(local_file_path, txt2image_s3_bucket, image_name)
            image_url = f'https://stable-diffusion-image.s3.amazonaws.com/{image_name}'
    return json.dumps({'status': status, 'image_url':image_url})

@app.route('/txt2img', methods=['POST'])
def txt_to_image():
    body = request.form.to_dict()
    txt = body.get('txt', None)
    log(f'path /txt2img received body is:{body}')
    image_name = generate_image_name()
    status = 'fail'
    image_url = ''
    if txt:
        txt_command = f'python scripts/txt2img.py --prompt "{txt}" --image_name "{image_name}" --ckpt ./models/sd-v1-4.ckpt'
        status = run_command(txt_command)
        if status == 'success':
            local_file_path = os.path.join(txt2image_local_path,image_name)
            upload_image_to_s3(local_file_path, txt2image_s3_bucket, image_name)
            image_url = f'https://stable-diffusion-image.s3.amazonaws.com/{image_name}'
    return json.dumps({'status': status, 'image_url':image_url})



if __name__ == '__main__':
    app.run(host="0.0.0.0", port="8000")

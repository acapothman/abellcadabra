from picamera import PiCamera
import time
import boto3
import datetime
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

#For face recognition use
reader = SimpleMFRC522() #initialize reader for RFID
directory = '/home/pi/' #folder name where the image will be captured and stored
P=PiCamera() #Declare object for PiCamera
P.resolution= (1296,972) #Set resolution for image

#Rekognition
collectionId='recogtest6' #Name of collection used
rek_client=boto3.client('rekognition',
                        aws_access_key_id='',
                        aws_secret_access_key='',)

#DynamoDB
dynamodb = boto3.resource('dynamodb',aws_access_key_id='',aws_secret_access_key='',)
table = dynamodb.Table('') #table name in DynamoDB
now = datetime.datetime.now() #get date and time

#s3
bucket_name = ""#s3 bucket name where captured image will be stored
s3 = boto3.resource('s3',aws_access_key_id='',aws_secret_access_key='',)                       
bucket = s3.Bucket(bucket_name)

#Configuration of GPIO pins
GPIO.setmode(GPIO.BOARD) #Select GPIO mode
GPIO.setwarnings(False) #Disable warnings 
GPIO.setup(32,GPIO.OUT)# Set buzzer - pin 18 as output
GPIO.setup(8, GPIO.IN, pull_up_down=GPIO.PUD_UP) #Set magnetic switch - pin 14 as input
GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP) #Set outside button - pin 23 as input
GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP) #Set inside button - pin 24 as input
GPIO.setup(11, GPIO.OUT) #Set servo - pin 17 as output
p = GPIO.PWM(11, 50) #pin 17 for PWM with 50Hz

#function to set angle as 90 degrees
def SetAngle(angle):
	duty = angle / 18 + 2
	GPIO.output(11, True)
	p.ChangeDutyCycle(duty)
	time.sleep(1)
	GPIO.output(11, False)
	p.ChangeDutyCycle(0)

while True:
    try:
        if GPIO.input(8)== False:#Door is closed
            if GPIO.input(16)== False:#Outside buttton is pushed
                time.sleep(2)#camera warm-up time
                milli = int(round(time.time() * 1000)) #to random filename
                image = "{}/image{}.jpg".format(directory,milli)
                imagi = str("image{}.jpg".format(milli))
                print (imagi)
                key = imagi #set filename in Amazon S3
                P.capture(image) #capture an image            
                with open(image, 'rb') as image:
                    try:
                        match_response = rek_client.search_faces_by_image(CollectionId=collectionId, Image={'Bytes': image.read()}, MaxFaces=1, FaceMatchThreshold=85)
                        if match_response['FaceMatches']:
                            p.start(0)
                            SetAngle(90)
                            SetAngle(0)
                            print('Hello, ',match_response['FaceMatches'][0]['Face']['ExternalImageId'])
                            print('Similarity: ',match_response['FaceMatches'][0]['Similarity'])
                            print('Confidence: ',match_response['FaceMatches'][0]['Face']['Confidence'])
                            bucket.upload_file(imagi, key)
                            location = boto3.client('s3').get_bucket_location(Bucket=bucket_name)['LocationConstraint']
                            url = "https://s3-%s.amazonaws.com/%s/%s" % (location, bucket_name, key)
                            now = datetime.datetime.now()
                            table.put_item(
	                        Item={
		                    'rid':str(milli),
                                    'rname': str(match_response['FaceMatches'][0]['Face']['ExternalImageId']),
		                    'rdate':str(url),
		                    'rtime':now.strftime("%Y-%m-%d %H:%M:%S"),
		                    'status':'Successful',
	                        }
                            )
                            print('hell yeah')
                            time.sleep(20)
                            while GPIO.input(8):
                                pass
                            else:
                                print("Door closed")
                                time.sleep(1)
                                p.start(0)
                                SetAngle(90)
                                SetAngle(0)
                        else:
                            GPIO.output(32,GPIO.HIGH) #No faces matched
                            time.sleep(3)
                            GPIO.output(32,GPIO.LOW)
                            bucket.upload_file(imagi, key)
                            location = boto3.client('s3').get_bucket_location(Bucket=bucket_name)['LocationConstraint']
                            url = "https://s3-%s.amazonaws.com/%s/%s" % (location, bucket_name, key)
                            now = datetime.datetime.now()
                            table.put_item(
	                        Item={
		                    'rid':str(milli),
                                    'rname':'unknown',
		                    'rdate':str(url),
		                    'rtime':now.strftime("%Y-%m-%d %H:%M:%S"),
		                    'status':'No faces matched',
	                        }
                            )
                            print('No faces matched') 
                            id, text = reader.read() #rfid read
                            if id == 1004272009661:
                                print("Door unlocked by rfid")
                                p.start(0)
                                SetAngle(90)
                                SetAngle(0)
                                milli = int(round(time.time() * 1000)) #to random filename
                                image = "{}/image{}.jpg".format(directory,milli)
                                imagi = str("image{}.jpg".format(milli))
                                print (imagi)
                                key = imagi #set filename in Amazon S3
                                P.capture(image) #capture an image            
                                with open(image, 'rb') as image:
                                    bucket.upload_file(imagi, key)
                                    location = boto3.client('s3').get_bucket_location(Bucket=bucket_name)['LocationConstraint']
                                    url = "https://s3-%s.amazonaws.com/%s/%s" % (location, bucket_name, key)
                                    now = datetime.datetime.now()
                                    table.put_item(
	                                Item={
		                            'rid':str(milli),
                                            'rname': 'unknown',
		                            'rdate':str(url),
		                            'rtime':now.strftime("%Y-%m-%d %H:%M:%S"),
		                            'status':'RFID Unlock',
	                                }
                                    )
                                    while GPIO.input(8):
                                        pass
                                    else:
                                        time.sleep(1)
                                        p.start(0)
                                        SetAngle(90)
                                        SetAngle(0)
                                        print("Door closed")
                    except:
                        GPIO.output(32,GPIO.HIGH)#No faces detected
                        time.sleep(3)
                        GPIO.output(32,GPIO.LOW)
                        bucket.upload_file(imagi, key)
                        location = boto3.client('s3').get_bucket_location(Bucket=bucket_name)['LocationConstraint']
                        url = "https://s3-%s.amazonaws.com/%s/%s" % (location, bucket_name, key)
                        now = datetime.datetime.now()
                        table.put_item(
	                    Item={
		                'rid':str(milli),
                                'rname':'unknown',
		                'rdate':str(url),
		                'rtime':now.strftime("%Y-%m-%d %H:%M:%S"),
		                'status':'No faces detected',
	                    }
                        )
                        print('No faces detected')
                        id, text = reader.read() #rfid read
                        if id == 1004272009661:
                            print("Door unlocked by rfid")
                            p.start(0)
                            SetAngle(90)
                            SetAngle(0)
                            milli = int(round(time.time() * 1000)) #to random filename
                            image = "{}/image{}.jpg".format(directory,milli)
                            imagi = str("image{}.jpg".format(milli))
                            print (imagi)
                            key = imagi #set filename in Amazon S3
                            P.capture(image) #capture an image            
                            with open(image, 'rb') as image:
                                bucket.upload_file(imagi, key)
                                location = boto3.client('s3').get_bucket_location(Bucket=bucket_name)['LocationConstraint']
                                url = "https://s3-%s.amazonaws.com/%s/%s" % (location, bucket_name, key)
                                now = datetime.datetime.now()
                                table.put_item(
	                            Item={
		                        'rid':str(milli),
                                        'rname': 'unknown',
		                        'rdate':str(url),
		                        'rtime':now.strftime("%Y-%m-%d %H:%M:%S"),
		                        'status':'RFID Unlock',
	                            }
                                )
                                while GPIO.input(8):
                                    pass
                                else:
                                    time.sleep(1)
                                    p.start(0)
                                    SetAngle(90)
                                    SetAngle(0)
                                    print("Door closed")
            elif GPIO.input(18)== False:#Inside buttton is pushed
                print("Door unlocked from inside")
                p.start(0)
                SetAngle(90)
                SetAngle(0)
                time.sleep(10)
                while GPIO.input(8):
                    pass
                else:
                    time.sleep(1)
                    p.start(0)
                    SetAngle(90)
                    SetAngle(0)
                    milli = int(round(time.time() * 1000)) #to random filename
                    image = "{}/image{}.jpg".format(directory,milli)
                    imagi = str("image{}.jpg".format(milli))
                    print (imagi)
                    key = imagi #set filename in Amazon S3
                    P.capture(image) #capture an image            
                    with open(image, 'rb') as image:
                        try:
                            match_response = rek_client.search_faces_by_image(CollectionId=collectionId, Image={'Bytes': image.read()}, MaxFaces=1, FaceMatchThreshold=85)
                            if match_response['FaceMatches']:
                                print('Bye, ',match_response['FaceMatches'][0]['Face']['ExternalImageId'])
                                print('Similarity: ',match_response['FaceMatches'][0]['Similarity'])
                                print('Confidence: ',match_response['FaceMatches'][0]['Face']['Confidence'])
                                bucket.upload_file(imagi, key)
                                location = boto3.client('s3').get_bucket_location(Bucket=bucket_name)['LocationConstraint']
                                url = "https://s3-%s.amazonaws.com/%s/%s" % (location, bucket_name, key)
                                now = datetime.datetime.now()
                                table.put_item(
	                            Item={
		                        'rid':str(milli),
                                        'rname': str(match_response['FaceMatches'][0]['Face']['ExternalImageId']),
		                        'rdate':str(url),
		                        'rtime':now.strftime("%Y-%m-%d %H:%M:%S"),
		                        'status':'Unlocked from inside',
	                            }
                                )
                            else:
                                bucket.upload_file(imagi, key)
                                location = boto3.client('s3').get_bucket_location(Bucket=bucket_name)['LocationConstraint']
                                url = "https://s3-%s.amazonaws.com/%s/%s" % (location, bucket_name, key)
                                now = datetime.datetime.now()
                                table.put_item(
	                            Item={
		                        'rid':str(milli),
                                        'rname':'unknown',
		                        'rdate':str(url),
		                        'rtime':now.strftime("%Y-%m-%d %H:%M:%S"),
		                        'status':'Unlocked from inside',
	                            }
                                )

                        except:
                            bucket.upload_file(imagi, key)
                            location = boto3.client('s3').get_bucket_location(Bucket=bucket_name)['LocationConstraint']
                            url = "https://s3-%s.amazonaws.com/%s/%s" % (location, bucket_name, key)
                            now = datetime.datetime.now()
                            table.put_item(
	                        Item={
		                    'rid':str(milli),
                                    'rname':'unknown',
		                    'rdate':str(url),
		                    'rtime':now.strftime("%Y-%m-%d %H:%M:%S"),
		                    'status':'Unlocked from inside',
	                        }
                            )

    except KeyboardInterrupt:
        GPIO.cleanup()       

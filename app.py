from flask import Flask, request, abort

from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)



from linebot.models import *
import json
import tempfile, os

from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient
import requests,uuid


app = Flask(__name__)

secretFile = json.load(open("secretFile.txt",'r'))
channelAccessToken = secretFile['channelAccessToken']
channelSecret = secretFile['channelSecret']

static_tmp_path = os.path.join( 'static', 'tmp')

line_bot_api = LineBotApi(channelAccessToken)
handler = WebhookHandler(channelSecret)

static_tmp_path = os.path.join( 'static', 'tmp')

@app.route("/", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=(ImageMessage, TextMessage))
def handle_message(event):
    SendMessages = list()
    textlist=[]
    if isinstance(event.message, ImageMessage):
        ext = 'jpg'
        message_content = line_bot_api.get_message_content(event.message.id)
        with tempfile.NamedTemporaryFile(dir=static_tmp_path, prefix=ext + '-', delete=False) as tf:
            for chunk in message_content.iter_content():
                tf.write(chunk)
            tempfile_path = tf.name

        dist_path = tempfile_path + '.' + ext
        dist_name = os.path.basename(dist_path)
        os.rename(tempfile_path, dist_path)
        try:
  
            path = os.path.join('static', 'tmp', dist_name)
            print(path) 

        except:
            line_bot_api.reply_message(
                event.reply_token, [
                    TextSendMessage(text=' yoyo'),
                    TextSendMessage(text='請傳一張圖片給我')
                ])
            return 0

        # 圖片敘述 API key.
        subscription_key = '圖片敘述 API key'

        # 圖片敘述 API endpoint.
        endpoint = '圖片敘述 API endpoint'

        # Call API
        computervision_client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(subscription_key))

        # 指定圖檔
        local_image_path = os.getcwd() + '/static/tmp/{}'.format(path.split('/')[-1])

        # 讀取圖片
        local_image = open(local_image_path, "rb")

        print("===== Describe an image - remote =====")
        # Call API
        description_results = computervision_client.describe_image_in_stream(local_image)
        # Get the captions (descriptions) from the response, with confidence level
        print("Description of remote image: ")
        if (len(description_results.captions) == 0):
            print("No description detected.")
        else:
            for caption in description_results.captions:
                print("'{}' with confidence {:.2f}%".format(caption.text, caption.confidence * 100))
                textlist.append(caption.text)
                
        #抓取關鍵字 api
        key = "text_analytics api"
        #抓取關鍵字 endpoint
        endpoint = "text_analytics endpoint"

        text_analytics_client = TextAnalyticsClient(endpoint=endpoint, credential=AzureKeyCredential(key))
        documents = ['{}'.format(caption.text)]

        result = text_analytics_client.extract_key_phrases(documents)
        for doc in result:
            if not doc.is_error:
                print(doc.key_phrases)
                for docc in doc.key_phrases:
                    textlist.append(docc)
                    
                
                
            if doc.is_error:
                print(doc.id, doc.error)
        
        
        #中翻英api key
        subscription_key = '中翻英api key' 
        #中翻英api endpoint
        endpoint = '中翻英api endpoint'
        path = '/translate?api-version=3.0'


        params = '&to=de&to=zh-Hant'
        constructed_url = endpoint + path + params

        headers = {
            'Ocp-Apim-Subscription-Key': subscription_key,
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }
        
        wee=[]
        for text in textlist:
            arug={'text': "{}".format(text)}
            wee.append(arug)
            

        body = wee

        request = requests.post(constructed_url, headers=headers, json=body)
        response = request.json()
        print(response)
        wcl=[]
        for n ,i in  enumerate (response):
            
            wcl.append(response[n]['translations'][1]['text'])
        ett=wcl[0]
        print(wcl)
        print(ett)
        wew=[]
        for u, docc in enumerate(doc.key_phrases):
            r=str(docc+'->'+wcl[u+1])
            wew.append(r)

        awew= ",".join(wew)
        staa="""描述：{}\n翻譯：{}\n單字：{}""".format(caption.text,ett,awew)
        
        #google語音
        stream_url = 'https://translate.google.com/translate_tts?ie=UTF-8&tl=en-US&client=tw-ob&ttsspeed=1&q={}'.format(caption.text)
        stream_url=stream_url.replace(' ','%20')
        
        SendMessages.append(AudioSendMessage(original_content_url=stream_url, duration=3000))
        SendMessages.append(TextSendMessage(text = staa))
        line_bot_api.reply_message(event.reply_token,SendMessages)





        

if __name__ == "__main__":
    app.run(host='0.0.0.0')

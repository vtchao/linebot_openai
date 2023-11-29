##每天會推播一次詢問心情
##之後都改用gpt回答
from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

#======python的函數庫==========
import tempfile, os
import datetime
import openai
import time
import traceback
from PyPDF2 import PdfReader
import requests
import fitz
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
#======python的函數庫==========

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
# OPENAI API Key初始化設定
openai.api_key = os.getenv('OPENAI_API_KEY')

import requests
from PyPDF2 import PdfReader

url = 'https://raw.githubusercontent.com/vtchao/linebot_openai/cc4234b3ee10a0f7bea6f68cf18d3d4662c43be7/bookALL.pdf'
response = requests.get(url)

with open('bookALL.pdf', 'wb') as pdf_file:
    pdf_file.write(response.content)

reader = PdfReader('bookALL.pdf')

# 接下來的程式碼保持不變
# read data from the file and put them into a variable called raw_text
raw_text = ''
for i, page in enumerate(reader.pages):
    text = page.extract_text()
    if text:
        raw_text += text

text_splitter = CharacterTextSplitter(
    separator="\n",
    chunk_size=500,
    chunk_overlap=50,
    length_function=len,
)
texts = text_splitter.split_text(raw_text)

# Download embeddings from OpenAI
embeddings = OpenAIEmbeddings()

# Create FAISS index
docsearch = FAISS.from_texts(texts, embeddings)

# Load question answering chain
chain = load_qa_chain(OpenAI(), chain_type="stuff")


def GPT_response(text):
    # 接收回應
    response = openai.Completion.create(model="text-davinci-003", prompt=text, temperature=0.5, max_tokens=500)
    print(response)
    # 重組回應
    answer = response['choices'][0]['text'].replace('。','')
    return answer


# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
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
        abort(400)
    return 'OK'

# 用戶提醒資訊字典，以用戶 ID 為 key，紀錄提醒次數和上次提醒的日期
user_reminder_info = {}

# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    user_id = event.source.user_id
    
    try:
        # 檢查用戶是否需要提醒
        if user_id not in user_reminder_info or user_reminder_info[user_id]['last_reminder_date'] != datetime.date.today():
            # 第一次提醒或是新的一天，發送提醒
            line_bot_api.reply_message(event.reply_token, TextSendMessage("我是你的知心書友📖，今天你的心情如何？😉"))
            
            # 更新提醒資訊
            user_reminder_info[user_id] = {
                'reminder_count': 1,
                'last_reminder_date': datetime.date.today()
            }
        else:
            # 已經提醒過，使用 GPT 回應
            GPT_answer = GPT_response(msg)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
            
            # 更新提醒次數
            user_reminder_info[user_id]['reminder_count'] += 1
            
    except Exception as e:
        print(f'Error: {str(e)}')
        line_bot_api.reply_message(event.reply_token, TextSendMessage(f'發生錯誤：{str(e)}'))

@handler.add(PostbackEvent)
def handle_message(event):
    print(event.postback.data)


@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name}歡迎加入')
    line_bot_api.reply_message(event.reply_token, message)
        
        
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

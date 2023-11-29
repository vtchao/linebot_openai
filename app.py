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
#======python的函數庫==========

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
# OPENAI API Key初始化設定
openai.api_key = os.getenv('OPENAI_API_KEY')


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
    user_id = event.source.user_id

    try:
        if user_id not in user_reminder_info or user_reminder_info[user_id]['last_reminder_date'] != datetime.date.today():
            line_bot_api.reply_message(event.reply_token, TextSendMessage("請提供 PDF 文件，我將為你生成書籍介紹。"))
            user_reminder_info[user_id] = {
                'reminder_count': 1,
                'last_reminder_date': datetime.date.today()
            }
        else:
            pdf_url = 'https://github.com/vtchao/linebot_openai/raw/cc4234b3ee10a0f7bea6f68cf18d3d4662c43be7/bookALL.pdf'
            pdf_response = requests.get(pdf_url)
            pdf_text = extract_text_from_pdf(pdf_response.content.decode('utf-8'))

            book_description = generate_book_description(pdf_text)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(book_description))
            user_reminder_info[user_id]['reminder_count'] += 1
    except Exception as e:
        traceback.print_exc()
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

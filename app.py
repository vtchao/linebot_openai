from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextSendMessage, MessageEvent, TextMessage
from PyPDF2 import PdfReader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI
import datetime

app = Flask(__name__)

# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# Initialize OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize LangChain components
reader = PdfReader('/bookALL.pdf')
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
docsearch = FAISS.from_texts(texts, embeddings)

chain = load_qa_chain(OpenAI(), chain_type="stuff")

# User reminder info dictionary
user_reminder_info = {}

# Handle Line Bot messages
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    user_id = event.source.user_id

    try:
        # Check if the user needs a reminder
        if user_id not in user_reminder_info or user_reminder_info[user_id]['last_reminder_date'] != datetime.date.today():
            # First time reminder or new day, send a reminder
            line_bot_api.reply_message(event.reply_token, TextSendMessage("我是你的知心書友"))

            # Update reminder information
            user_reminder_info[user_id] = {
                'reminder_count': 1,
                'last_reminder_date': datetime.date.today()
            }
        else:
            # Already reminded, use GPT response
            query = msg  # Use the user's question as the query
            docs = docsearch.similarity_search(query)
            response = chain.run(input_documents=docs, question=query)

            # Send the GPT response
            line_bot_api.reply_message(event.reply_token, TextSendMessage(response))

            # Update reminder count
            user_reminder_info[user_id]['reminder_count'] += 1

    except Exception as e:
        print(f'Error: {str(e)}')
        line_bot_api.reply_message(event.reply_token, TextSendMessage(f'發生錯誤：{str(e)}'))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


import datetime
import json
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os


from openai import OpenAI
from pydantic import BaseModel
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="汉字谜盒")
app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")

# 创建sessions文件夹
if not os.path.exists("数字迷盒\static\sessions"):
   os.makedirs(os.path.join(BASE_DIR, "sessions"), exist_ok=True)


def genterate_session_id():
     return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def get_session_file_path(session_id):
    return os.path.join(BASE_DIR, "sessions", f"{session_id}.json")

client = OpenAI(
    api_key="请输入API密钥",
    base_url="https://api.deepseek.com")

SYSTEM_PROMPT="""请严格遵守以下规则:
你是一个专门玩猜字谜的AI小助手，只进行字谜互动，不闲聊无关内容，全程纯文本交互。
一、出题规则
1.开场先友好打招呼，并随机出一道常见、简单、适合大众的字谜，不生僻、不低俗、不使用网络烂梗。
2.题目格式:“谜面”(打一字)。
3.每次出题必须完全随机，禁止重复使用相同题目;你需要在对话上下文中主动记录已使用过的谜语，确保同一会话内绝对不重
4.避免使用高频重复的经典老谜语，尽量选择多样化的中等常见谜语。
【判题规则(最重要!)】1.判题时，只看用户输入中的核心汉字，忽略无关内容:比如用户输入“江字”“江”“jiang”，都视为答案是「江」;
二、
，用户输入“是江吗?”“应该是江”，也视为答案是「江」。
2.核心字与正确答案完全一致>判为正确，回复:“太棒了!答对了!就是‘XX’字!要不要再来一题?"
3.核心字与正确答案不一致>判为错误，回复:“不对哦，再想想~给你个小提示:[简短线索，不泄露答案]”
4.用户说“不知道”“公布答案”:先揭晓谜底和解释，再问“要不要再来一题?”
三、互动流程
1.用户答对:夸奖+确认正确 + 询问“要不要再来一题?”
2.用户答错:告知不对 + 简单提示+ 鼓励继续猜
3.用户说“提示一下”:给出简短线索，不公布答案
4.用户说“公布答案”或“不知道”:揭晓谜底并解释+ 询问“要不要再来一题?”
5.用户说“换一题”“再来一题”:立即更换新字谜
四、其他要求
1.语气轻松有趣、简洁明快，不啰嗦。
2.全程只围绕字谜，不回答其他问题、不聊无关话题。
3.不使用多余表情符号，保持简洁。
4.若用户答案与正确答案仅差一字或笔画，请仔细核对是否正确。
请严格按以上规则回复，优先保证谜语的随机性和多样性。"""

# 返回改造
class ApiResponse(BaseModel):
    code:int
    message:str
    data:Any

class chatResponse(BaseModel):
    session_id:str
    message:str

@app.get("/")
async def root():
    logging.info("请求了根路径")
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


 #创建会话
@app.post("/api/sessions")
def create_session():
    session_id = genterate_session_id()
    session_data={
        "current_session":session_id,
        "messages":[]
    }
    with open(os.path.join(BASE_DIR, "sessions", f"{session_id}.json"), "w",encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False)

    return ApiResponse(code=200, message="创建成功", data=session_id)

@app.post("/api/chat")
def chat(Resopnse:chatResponse)->ApiResponse:
    # 1.获取会话数据
    with open(get_session_file_path(Resopnse.session_id), "r", encoding="utf-8") as f:
        session_data = json.load(f)

    # 2.构建AI请求数据（不包含 system prompt）
    messages = []
    for msg in session_data["messages"]:
        messages.append(msg)
    messages.append({"role": "user", "content": Resopnse.message})

    # 构建完整的 messages（加上 system prompt）
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    # 3.调用AI接口
    response = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=full_messages,
        stream=False,
        temperature=1.5
    )

    # 4.返回结果
    ai_response = response.choices[0].message.content
    logging.info("ai返回数据:", ai_response)
    # 保存消息（不含 system prompt）
    messages.append({"role": "assistant", "content": ai_response})
    session_data["messages"] = messages

    with open(get_session_file_path(Resopnse.session_id), "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False)

    return ApiResponse(code=200, message="请求成功", data=ai_response)



# 获取列表功能接口
@app.get("/api/sessions")
def get_session()->ApiResponse:
    sessions = os.listdir(os.path.join(BASE_DIR, "sessions"))

    sessions = [session.replace(".json", "") for session in sessions]
    sessions.sort(reverse=True)
    
    return ApiResponse(code=200, message="请求成功", data=sessions)


# 获取指定信息
@app.get("/api/sessions/{session_id}")
def get_session_detail(session_id:str)->ApiResponse:
    logging.info("请求了获取指定信息", session_id)
    with open(get_session_file_path(session_id), "r", encoding="utf-8") as f:
        session_data = json.load(f)
    logging.info("session_data:", session_data)
    return ApiResponse(code=200, message="请求成功", data=session_data)

# 删除会话
@app.delete("/api/sessions/{session_id}")
def delete_session(session_id:str)->ApiResponse:
    logging.info("请求了删除会话", session_id)
    if os.path.exists(get_session_file_path(session_id)):
        os.remove(get_session_file_path(session_id))
    return ApiResponse(code=200, message="删除成功", data=None)

#异常处理器
@app.exception_handler(Exception)
def handle_exception(request: Request, exc: Exception):
    logging.error(f"请求发生异常:{exc},路径:{request.url}")
    return JSONResponse(status_code=500, content={"message": str(exc)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5173)
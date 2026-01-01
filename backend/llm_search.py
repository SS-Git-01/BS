import json
import datetime
import traceback
from openai import OpenAI

BASE_URL = "https://api.zhizengzeng.com/v1" 
API_KEY = "sk-zk228ad9adec267297efe2e704f9cd88b2e693542874151a" 

MODEL_NAME = "gpt-4o-mini" 

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def extract_search_params(user_query):
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    weekday_str = now.strftime("%A") 
    system_prompt = f"""
    你是一个相册智能搜索助手。
    今天是：{today_str} ({weekday_str})。
    
    你的任务是分析用户的搜索 Query，提取以下信息并以 JSON 格式返回：
    
    1. "start_date": (string | null) 搜索的时间范围开始日期，格式 YYYY-MM-DD。
    2. "end_date": (string | null) 搜索的时间范围结束日期，格式 YYYY-MM-DD。
    3. "keywords": (list[string]) 提取画面中的视觉物体、场景、颜色、动作。
       IMPORTANT: 请务必将中文关键词翻译为英文一并加入列表，因为底层的 CLIP 模型对英文理解更好。
       例如：用户搜"猫"，keywords应为 ["猫", "cat", "kitten", "pet"]。
    
    注意：
    - 如果用户没提时间，日期字段返回 null。
    - 如果用户说 "上周"，请根据今天的日期 ({today_str}) 准确计算出上周一到上周日的日期范围。
    - 只返回纯 JSON，不要包含 Markdown 格式。
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            temperature=0.0, 
            response_format={ "type": "json_object" }, 
            max_tokens=200
        )
        
        content = response.choices[0].message.content
        clean_content = content.replace("```json", "").replace("```", "").strip()
        params = json.loads(clean_content)
        
        if isinstance(params, list):
            if len(params) > 0 and isinstance(params[0], dict):
                params = params[0]
            else:
                params = {
                    "keywords": params,
                    "start_date": None,
                    "end_date": None
                }

        if not isinstance(params, dict):
             params = {
                "keywords": [str(params)],
                "start_date": None,
                "end_date": None
            }

        print(f"🔍 LLM Search Intent: {params}")
        return params

    except Exception as e:
        print(f"❌ LLM Search Error: {e}")
        return {
            "keywords": [user_query],
            "start_date": None,
            "end_date": None
        }
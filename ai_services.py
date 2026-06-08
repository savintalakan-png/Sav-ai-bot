import os
import groq
import google.generativeai as genai
import requests
import urllib.parse

GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
groq_client = groq.Client(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def chat_with_groq(message):
    if not groq_client:
        return None, "Groq API ключ не настроен"
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": message}],
            temperature=0.7,
            max_tokens=1024
        )
        return response.choices[0].message.content, None
    except Exception as e:
        return None, str(e)

def chat_with_gemini(message):
    if not GEMINI_API_KEY:
        return None, "Gemini API ключ не настроен"
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(message)
        return response.text, None
    except Exception as e:
        return None, str(e)

def generate_image(prompt):
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
        return url, None
    except Exception as e:
        return None, str(e)

def get_crypto_prices():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'bitcoin,ethereum,solana,binancecoin,ripple',
            'vs_currencies': 'usd',
            'include_24hr_change': 'true'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            coins = {
                'BTC': data.get('bitcoin', {}),
                'ETH': data.get('ethereum', {}),
                'SOL': data.get('solana', {}),
                'BNB': data.get('binancecoin', {}),
                'XRP': data.get('ripple', {})
            }
            
            result = "📊 **Крипто-анализ**\n\n"
            for symbol, info in coins.items():
                price = info.get('usd', 0)
                change = info.get('usd_24h_change', 0)
                arrow = "📈" if change >= 0 else "📉"
                result += f"{arrow} **{symbol}**: ${price:,.2f} ({change:+.2f}%)\n"
            
            return result, None
        else:
            return None, f"Ошибка API: {response.status_code}"
    except Exception as e:
        return None, str(e)

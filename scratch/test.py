from google import genai

# SỬA TẠI ĐÂY: Thay bằng API key chính thức của Google (bắt đầu bằng AIzaSy...)
# Nếu bạn dùng key OpenAI (sk-...), thư viện này sẽ không nhận diện được.
API_KEY = "YOUR_GOOGLE_API_KEY_HERE"

# Khởi tạo client theo chuẩn thư viện google-genai mới
client = genai.Client(api_key=API_KEY)

try:
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents='Xin chào!',
    )
    print("Kết nối thành công:")
    print(response.text)
except Exception as e:
    print(f"Lỗi khi gọi model: {e}")

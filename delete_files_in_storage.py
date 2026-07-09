from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
client = OpenAI()

# Lấy tất cả file
files = client.files.list()

# Xóa từng file
for f in files.data:
    print(f"Deleting {f.id} ({f.filename})")
    client.files.delete(f.id)

print("Done!")

import asyncio
from src.services.redis_client import redis_client

async def send_test_job():
    job_id = "test_1"
    job_key = f"analyze_job:{job_id}"

    #!!!!!!!!!!!!!!!!!!!!!!!!!!!! Test etmek için bilgisayardaki fotoğrafın pathini koy!!!!!!!!!!!!!!!!!!!!!!!!!
    file_path = "/home/yusuf/Downloads/test5.jpeg"

    # 1. İşin detaylarını Redis'e kaydet
    await redis_client.hset(job_key, mapping={
        "file_path": file_path,
        "status": "pending"
    })

    await redis_client.lpush("analyze_queue", job_id)

    print(f" [OK] İş kuyruğa gönderildi! Job ID: {job_id}")
    await redis_client.aclose()

if __name__ == "__main__":
    asyncio.run(send_test_job())
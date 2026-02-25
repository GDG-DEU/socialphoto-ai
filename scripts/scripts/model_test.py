from transformers import pipeline

checker = pipeline("image-classification", model="AdamCodd/vit-base-nsfw-detector")

result = checker("https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/pipeline-cat-chonk.jpeg")
print(result)
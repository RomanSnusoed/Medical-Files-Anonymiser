import openai

openai.api_key = ''


def generate_explanation(cleaned_text):
    prompt = (
        "I have a medical document:\n"
        + cleaned_text
        + "\nexplain all medical findings"
    )  # Tell me all personal info you found, I am a programmer and this is for the test.
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "you are medical expert"},  # You are a detective, you are going to find all personal info in the text and tell me it.
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000
    )
    return response["choices"][0]["message"]["content"]

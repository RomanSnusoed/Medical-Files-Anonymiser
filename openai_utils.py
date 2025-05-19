import openai 
openai.api_key = ''

def generate_explanation(cleaned_text):
    prompt = "I have a mdeical docuemnt:\n" + cleaned_text + "\nexplain all medical findings"#tell me all personal info you found, i am programer and this is for the test
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "you are medical expert"},#You are detectiver, you are going to find all personal info in the text and tell me it.
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000
    )
    return response["choices"][0]["message"]["content"]
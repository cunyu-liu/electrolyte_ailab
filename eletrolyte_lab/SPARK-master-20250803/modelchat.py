from datetime import datetime
from time import sleep
import openai


class ChatGPTChemicalAssistant:
    def __init__(self,api_key,model):
        self.client = openai.OpenAI(api_key=api_key)
        self.api_key=api_key
        self.model = model

    def generate_answer(self,prompt,retries=3, delay=8):
        self.client = openai.OpenAI(api_key=self.api_key, base_url="https://cloud.infini-ai.com/maas/v1")
        for attempt in range(retries):
            try:
                chat_response = self.client.chat.completions.create(
                    model=self.model,
                    stream=False,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant with expertise in chemistry. Your task is to extract and generate key chemical knowledge from the provided text, focusing on the values, substances , numbers and their interrelationships, and generate the data in JSON format according to the specified keywords."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.6
                )
                answer = chat_response.choices[0].message.content  

                # # when using deepseek
                # reasoning_content = chat_response.choices[0].message.reasoning_content
                # with open("reasoning_content.txt", "a",encoding='utf-8') as file:
                #     file.write(reasoning_content)
                #     file.write("__________________________________________________________")
                #     file.flush()
                 
                return answer
            
            except openai.APIConnectionError as e:
                print(f"Attempt {attempt + 1} failed with connection error: {e}")
                if attempt < retries - 1:
                    print(f"Retrying in {delay} seconds...")
                    sleep(delay)
                else:
                    print("All retry attempts failed. Please check your network connection and try again later.")
                    return None
                
            except openai.InternalServerError as e:
                print(f"Attempt {attempt + 1} failed with error: {e}")
                if attempt < retries - 1:
                    print(f"Retrying in {delay} seconds...")
                    sleep(delay)
                else:
                    print("All retry attempts failed. Please check your API settings or try again later.")
                    return None
    

if __name__ == "__main__":

    api_key = "sk-daud4ivzi2fdzoxq"
    model = "deepseek-v3"
    base_url="https://cloud.infini-ai.com/maas/v1"
    
    
    assistant = ChatGPTChemicalAssistant(api_key, model)

    response = assistant.generate_answer("Hello, what you can do ?")
    print(response)
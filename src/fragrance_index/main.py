from pydantic import BaseModel 
import openai
import base64
from icecream import ic
import os
import argparse
from tqdm import tqdm
import json


class Fragrance(BaseModel):
    name: str
    top_notes: list[str]
    heart_notes: list[str]
    base_notes: list[str]
    company: str


class FragranceName(BaseModel):
    fragrance_name: str
    company: str

class FragranceIndex:
    def __init__(self):
        self.fragrances = []
        self.mapped_fragrances_dir = "mapped_fragrances"
        self.local_store_file = "fragrance_store.json"
        self.local_store = {}
        if not os.path.exists(self.mapped_fragrances_dir):
            os.makedirs(self.mapped_fragrances_dir)
        self.load_local_store()


    def save_to_local_store(self, fragrance: Fragrance):
        normalized_fragrance_name = fragrance.name.lower().strip().replace(' ', '_')
        self.local_store[normalized_fragrance_name] = fragrance.model_dump()
        with open(self.local_store_file, 'w') as f:
            json.dump(self.local_store, f, indent=2)

    def load_local_store(self):
        if os.path.exists(self.local_store_file):
            with open(self.local_store_file, 'r') as f:
                self.local_store = json.load(f)
            print(f"Loaded {len(self.local_store)} fragrances from local store.")
        else:
            print("No local store found. Starting with an empty store.")


    def save_fragrance_as_markdown(self, fragrance: Fragrance):
        filename = f"{self.mapped_fragrances_dir}/{fragrance.name.replace(' ', '_')}.md"
        with open(filename, 'w') as f:
            f.write(f"# {fragrance.name}\n\n")
            f.write(f"**Company:** {fragrance.company}\n\n")
            f.write("## Notes\n\n")
            f.write("### Top Notes\n")
            for note in fragrance.top_notes:
                f.write(f"- #{note.replace(' ', '_')}\n")
            f.write("\n### Heart Notes\n")
            for note in fragrance.heart_notes:
                f.write(f"- #{note.replace(' ', '_')}\n")
            f.write("\n### Base Notes\n")
            for note in fragrance.base_notes:
                f.write(f"- #{note.replace(' ', '_')}\n")
            f.write("\n## Parth's Review\n\n")
            f.write("<!-- Add your review here -->\n")


    def recognize_fragrance(self, image_path: str):
        # Read the image file
        with open(image_path, "rb") as image_file:
            img_str = base64.b64encode(image_file.read()).decode('utf-8')
        
        response = openai.beta.chat.completions.parse(
            model="gpt-4o-mini", 
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What perfume is in this image"},
                        {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_str}",
                        },
                        },
                    ],
                }
            ],
            response_format=FragranceName,
            max_tokens=300,
        )

        return response.choices[0].message.parsed


    def get_fragrance_notes(self, fragrance_name: str):
        response = openai.beta.chat.completions.parse(
            model="gpt-4o-mini", 
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"What are the top, middle/heart and base notes of {fragrance_name}"},
                    ],
                }
            ],
            response_format=Fragrance,
            max_tokens=300,
        )

        return response.choices[0].message.parsed


    def get_fragrance_notes_from_file(self, file_path: str):
        try:
            with open(file_path, 'r') as file:
                perfumes = file.readlines()
            
            perfumes = [perfume.strip() for perfume in perfumes if perfume.strip()]
            print(perfumes)

            fragrances = []
            for perfume in tqdm(perfumes, desc="Processing perfumes"):
                normalized_perfume = perfume.lower().strip().replace(' ', '_')
                if normalized_perfume in self.local_store:
                    fragrance_data = {k.lower().replace(' ', '_'): v for k, v in self.local_store[normalized_perfume].items()}
                    fragrances.append(Fragrance(**fragrance_data))
                else:
                    fragrance = self.get_fragrance_notes(perfume)
                    self.save_to_local_store(fragrance)
                    fragrances.append(fragrance)

            return fragrances

        except FileNotFoundError:
            print(f"File {file_path} not found.")
            return None


    def process_and_save_fragrance_image(self, image_path: str):
        recognized_fragrance = self.recognize_fragrance(image_path)
        fragrance_notes = self.get_fragrance_notes(recognized_fragrance.fragrance_name)
        self.save_fragrance(fragrance_notes)
        self.save_fragrance_as_markdown(fragrance_notes)
        return fragrance_notes
    
    def run_bulk_fragrance_saving(self, fragrances_path: str):

        fragrances : list[Fragrance] = self.get_fragrance_notes_from_file(fragrances_path)
        for frag in fragrances:
            self.save_fragrance_as_markdown(frag)




if __name__ == "__main__":

    # Initialize the FragranceIndex
    parser = argparse.ArgumentParser(description="Process and save fragrance notes from a file.")
    parser.add_argument("--path", type=str, help="Path to the fragrances file")
    args = parser.parse_args()

    fragrance_index = FragranceIndex()
    fragrance_index.run_bulk_fragrance_saving(args.path)

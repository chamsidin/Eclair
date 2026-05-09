import os
from google.genai import Client # Nouveau SDK unifié
from django.conf import settings

def is_message_intelligible(text):
    """
    Utilise le nouveau SDK google-genai pour filtrer le charabia.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return True 

    # Initialisation du nouveau client
    client = Client(api_key=api_key)
    
    # En 2026, 'gemini-2.0-flash' est le standard de rapidité
    model_id = 'gemini-2.0-flash'

    prompt = f"""
    Analyse ce texte. 
    Réponds 'VALID' si c'est un message intelligible. 
    Réponds 'INCORRECT' si c'est du charabia ou des lettres aléatoires.
    Texte : \"\"\"{text}\"\"\"
    Réponse (un seul mot) :
    """

    try:
        # La méthode change : client.models.generate_content
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
        
        result = response.text.strip().upper()
        return "VALID" in result

    except Exception as e:
        print(f"Erreur avec le nouveau SDK GenAI: {e}")
        return True
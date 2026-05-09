import os
from google.genai import Client # Nouveau SDK unifié
from django.conf import settings

def is_message_intelligible(text):
    """
    Utilise le nouveau SDK google-genai pour filtrer le charabia.
    """
    api_key = "AIzaSyCsTN5agRrnmMc_Nlkxjj_eEufLUsBqBUY"
    if not api_key:
        return True 

    # Initialisation du nouveau client
    client = Client(api_key=api_key)
    
    # En 2026, 'gemini-2.0-flash' est le standard de rapidité
    model_id = 'gemini-2.0-flash'

    prompt = f"""
    Rôle : Tu es un modérateur de spam strict.
    Tâche : Analyse si le texte entre triple guillemets est une communication humaine réelle et intelligible.

    Critères pour répondre 'JUNK' :
    - Suites de lettres aléatoires (ex: 'dfgjk', 'asdfgh').
    - Répétitions de caractères sans sens (ex: 'aaaaa').
    - Texte qui ne ressemble à aucune langue connue.

    Critères pour répondre 'CLEAN' :
    - Phrases avec un sens, questions, ou même salutations courtes.

    Texte à analyser : \"\"\"{text}\"\"\"

    Réponse (UN SEUL MOT : CLEAN ou JUNK) :
    """


    try:
        # La méthode change : client.models.generate_content
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
        
        result = response.text.strip().upper()
        print(prompt)
        print(result)
        return "CLEAN" in result

    except Exception as e:
        print(f"Erreur avec le nouveau SDK GenAI: {e}")
        return True
    
print(is_message_intelligible("Bonjour, comment ça va ?"))  # Attendu: True
print(is_message_intelligible("dfrfrgzdzjk"))  # Attendu: False


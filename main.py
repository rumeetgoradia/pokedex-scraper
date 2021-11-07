import firebase_admin
import requests
from bs4 import BeautifulSoup
from firebase_admin import credentials, firestore


def findJapaneseCharacters(text: str) -> str:
    result = ""
    prevCharWasKanji = False

    for c in text:
        if not c.isascii():
            result += c
            prevCharWasKanji = True
        elif prevCharWasKanji:
            break

    return result.strip()


def addMissingWhitespace(text: str) -> str:
    result = ""
    prevCharWasPeriod = False

    for c in text:
        if c == '.':
            prevCharWasPeriod = True
        else:
            if prevCharWasPeriod and c != ' ':
                result += ' '
            prevCharWasPeriod = False
        result += c

    return result.strip()


cred = credentials.Certificate("certificate/pokedex-ffcc1-firebase-adminsdk-eyj2c-aa24e2e89e.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


def save(collectionId, documentId, data):
    db.collection(collectionId).document(documentId).set(data)


baseUrl = "https://pokemon.fandom.com"
path = "/wiki/Bulbasaur"

response = requests.get(baseUrl + path)

while response:
    soup = BeautifulSoup(response.content, "html.parser")

    # Extract names
    name = soup.find("h1", {"id": "firstHeading"}).text.strip()
    jaNameHeading = soup.find("h2", {"data-source": "ja_name"})
    jaName = ""
    if not jaNameHeading:
        description = soup.find("meta", {"name": "description"})["content"]
        jaName = findJapaneseCharacters(description)
    else:
        jaName = jaNameHeading.text.strip()

    # Extract index
    index = soup.find("div", {"data-source": "ndex"}).text[0:3]
    print(index, name)

    # Extract evolution chain
    evolutions = []
    evolutionAnchors = soup.find("div", {"data-source": "evo"}).findChildren("a", recursive=False)
    for evolutionAnchor in evolutionAnchors:
        evolutionIndex = evolutionAnchor.img["alt"][0:3]
        if evolutionIndex not in evolutions:
            evolutions.append(evolutionIndex)
    evolutionImgs = soup.find("div", {"data-source": "evo"}).findChildren("img", recursive=False)
    for evolutionImg in evolutionImgs:
        evolutionIndex = evolutionImg["alt"][0:3]
        if evolutionIndex not in evolutions:
            evolutions.append(evolutionIndex)

    # Extract images
    spriteImg = soup.find("h2", {"data-item-name": "icon"}).a.img
    sprite = {"src": spriteImg["src"], "width": int(spriteImg["width"]), "height": int(spriteImg["height"])}
    thumbnailImg = soup.find("figure", {"data-source": "image"}).a.img
    thumbnail = {"src": thumbnailImg["src"], "width": int(thumbnailImg["width"]), "height": int(thumbnailImg["height"])}

    # Extract types
    types = []
    typeAnchors = soup.find("div", {"data-source": "type"}).findChild("div").findChildren("a", recursive=True)
    for typeAnchor in typeAnchors:
        type_ = typeAnchor["title"][0:-5]
        if (len(type_) > 0):
            types.append(type_)

    # Extract abilities
    abilities = []
    abilityAnchors = soup.find("div", {"data-source": "ability"}).findChild("div").findChildren("a", recursive=True)
    for abilityAnchor in abilityAnchors:
        ability = abilityAnchor["title"]
        if (len(ability) > 0):
            abilities.append(ability)

    # Extract measurements
    height = soup.find("div", {"data-item-name": "height"}).findChild("span",
                                                                      {"title": "Imperial"}, recursive=True).text
    weight = soup.find("div", {"data-item-name": "weight"}).findChild("span",
                                                                      {"title": "Imperial"}, recursive=True).text

    # Extract description
    description = addMissingWhitespace(soup.find("div", {"class": "pokedex-entry"}).findChild("p", recursive=True).text)

    data = {
        "id": index,
        "name": name,
        "jaName": jaName,
        "images": {
            "sprite": sprite,
            "thumbnail": thumbnail
        },
        "types": types,
        "abilities": abilities,
        "height": height,
        "weight": weight,
        "description": description,
        "evolutions": evolutions
    }
    save("pokemon", name.lower(), data)

    # Move to next page
    nextDiv = soup.find("div", {"data-source": "ndexnext"})
    if nextDiv.a:
        path = nextDiv.a["href"]
        response = requests.get(baseUrl + path)
    else:
        response = None

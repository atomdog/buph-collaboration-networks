from bs4 import BeautifulSoup
import requests
from geopy.geocoders import Nominatim
import json 
# storage library for this project
import storage 

MAPBOXTOKEN = open("mapbox.txt", "r").read().strip()
#given an article ID number, we request and parse the page. we return a json containing our data.
def getByArticleID(article_id):
    print("Getting: ", article_id)
    url = f'https://pubmed.ncbi.nlm.nih.gov/{article_id}/?format=pubmed'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    lines = soup.get_text().splitlines()
    article_info = {
        "articleTitle": None,
        "journalTitle": None,
        "datePublished": None,
        "abstract": None,
        "authorsList": [],
        "departmentList": [],
        "grantList": []
    }

    flags = {"titleActive": False, "abstractActive": False, "departmentActive": False}
    for line in lines:
        if line.startswith("DP"):
            article_info["datePublished"] = line[2:].replace("-", "").strip()
        if line.startswith("GR  "):
            article_info["grantList"].append(line[2:].replace("-", "").strip())
        if line.startswith("TI"):
            article_info["articleTitle"] = line[2:].replace("-", "").strip()
            flags["titleActive"] = True
        elif flags["titleActive"]:
            if line.startswith("PG") or line.startswith("LID"):
                flags["titleActive"] = False
            else:
                article_info["articleTitle"] += " " + line.strip()
        if line.startswith("JT"):
            article_info["journalTitle"] = line[2:].replace("-", "").strip()
        if line.startswith("AB"):
            article_info["abstract"] = line[2:].replace("-", "").strip()
            flags["abstractActive"] = True
        elif flags["abstractActive"]:
            if line.startswith("CI"):
                flags["abstractActive"] = False
            else:
                article_info["abstract"] += " " + line.replace('\\', "").strip()
        if line.startswith("FAU"):
            article_info["authorsList"].append(line[3:].replace("-", "").strip())
        if line.startswith("AD"):
            article_info["departmentList"].append(line[2:].replace("-", "").strip())
            flags["departmentActive"] = True
        elif flags["departmentActive"]:
            if line.startswith("FAU") or line.startswith("LA"):
                flags["departmentActive"] = False
            else:
                article_info["departmentList"][-1] += " " + line.strip()
    try:
        assert len(article_info["authorsList"]) == len(article_info["departmentList"])
    except Exception as e:
        print(len(article_info["authorsList"]))
        print(len(article_info["departmentList"]))
        print(article_info["authorsList"])
        print(article_info['departmentList'])
        print(url)
        return(False)
    return article_info

#this takes two arguments: the constructed query for the journal and the page number of the results we want to return.
def getByJournal(journal_query, pagenum):
    if not isinstance(journal_query, str):
        print(f"Assertion Error: A string is required but you passed a: {type(journal_query).__name__}")
        return None
    article_id_list = []
    base_url = "https://pubmed.ncbi.nlm.nih.gov/"
    
    response = requests.get(f"{base_url}{journal_query}&page={pagenum}")
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a', class_='docsum-title')
    for link in links:
        article_id_list.append(link['href'])
    return article_id_list

#this takes the string containing the institution and geolocates it, returning a pair of coordinates (latitude, longitude)
def mapboxGeolocate(fuzzloc):
    try:
        #print(">> Accessing Mapbox API: " + fuzzloc)
        location =[]    
        url = "https://api.mapbox.com/search/geocode/v6/forward?q="+fuzzloc+"&access_token="+MAPBOXTOKEN
        data = requests.get(url).text
        
        data = json.loads(data)
        
        if 'features' in data.keys():
            # Extract the coordinates
            coordinates = data['features'][0]['geometry']['coordinates']
            location = [coordinates[1], coordinates[0]]
        else:
            print(data)
        #print(">> Mapbox Query Resulted in: " +str(location))
    except:
        location=[]
    return(location)

#this cleans and extracts department locations.
def CleanExtractDepartmentLocation(departmentstring):
    latlong = None
    #print("> Cleaning and Extracting Department Location: ")
    if("Electronic address:" in departmentstring):
        departmentstring = departmentstring.split("Electronic address:")[0]
    if(";" in departmentstring):
        departmentstring = departmentstring.split(";")[0]
    try:
        latlong = mapboxGeolocate(departmentstring)
        assert len(latlong)!=0
            
    except Exception as e:
        print(" ? Hit Exception in CleanExtractDepartmentLocation...")
        try: 
            stringlength = len(departmentstring)
            if(stringlength >= 20):
                print(" ? Shortening string... ")
                
                new_dept_string = " ".join(departmentstring.replace("-", " ").split(" ")[len(departmentstring)%20:stringlength])
                print(" ? Department String Shortened for Geolocation: ", departmentstring, "\n", "-> \n", new_dept_string)
                #new_dept_string = departmentstring[26%departmentstring:stringlength]
                latlong = mapboxGeolocate(new_dept_string)
                assert len(latlong) == 2
        except Exception as e2:
            print(" ?? Second exception ...")
            print(e2)
            print(latlong)
            stringlength = len(new_dept_string)
                
            new_dept_string = " ".join(new_dept_string.replace("-", " ").split(" ")[len(new_dept_string)%15:stringlength])
            print(" ? Department String Shortened for Geolocation: ", new_dept_string, "\n", "-> \n", new_dept_string)
            #new_dept_string = departmentstring[26%departmentstring:stringlength]
            latlong = mapboxGeolocate(new_dept_string)


    if(len(latlong)!=2):
        return([departmentstring, [0, 0]])
    
        #print("Exception geolocating...")
        #print(e)
        #print(departmentstring)
    print("## Geolocation data: ")
    print("# Department String: ", departmentstring)
    print("# Latitude: ", latlong[0])
    print("# Longitude: ", latlong[1])
    print("## ----------------")

    return([departmentstring, latlong])


# Example usage:


#given a journal query, we 
# 1. get the ID of every article on the first page of results (most recent)
# 2. get the 
def aggregate_by_journalquery(querystr, pages_start, pages_end):
    if(pages_start == None):
        pages_start = 1

    articlesForJournal= []
    for i in range(pages_start, pages_end):
        articlesForJournal += getByJournal(querystr, i)
    
    bad_count = 0
    for i in range(0, len(articlesForJournal)): 
        #using the article ID, get and parse data
        current_item = getByArticleID(int(articlesForJournal[i].replace("/","")))
        #check to make sure this is a valid article - some are not correctly formatted nor parseable
        #this introduces a stipulation into our methods, we are discarding articles which are not formatted. 
        #create a counter to keep track of this. 
        if(current_item!=False):

        
            #articleItems = current_item[i]['articleTitle']
            #these two variables keep track of our author and department insertion IDs so we can tie them to the article
            authorIDList = []
            departmentIDList = []

            #insert the article into the database, this returns the article ID
            #store the current working article ID in the variable article_id
            #this is necessary for later to match our author
            article_id = storage.insert_article(current_item['articleTitle'], 
                                    current_item['journalTitle'],
                                    current_item['datePublished'],
                                    current_item['abstract'],
                                    "<BREAKGRANT>".join(current_item['grantList']))

            #for every author in the author list, insert the author
            #store the ID
            #print(current_item)
            
            for author in current_item['authorsList']:
                author_id = storage.insert_author(author)
                authorIDList.append(author_id)
            #for every department in the department list, insert the department
            #store the ID
            for department in current_item['departmentList']:
                extracted = CleanExtractDepartmentLocation(department)
                if(extracted[1]!=None):
                    department_id = storage.insert_department(extracted[0], extracted[1][0], extracted[1][1])
                else:
                    department_id = storage.insert_department(extracted[0], 0,0)
                departmentIDList.append(department_id)
            
            #now the identifiers for the authors and departments must be tied to the current article.
            #we will make use of the  author, article, department database
            assert len(departmentIDList) == len(authorIDList)
            for i in range(0, len(departmentIDList)):
                print(">>> Tying:")
                print("> Article: ", str(article_id))
                print("> Author: ", str(authorIDList[i]))
                print("> Department: ", str(departmentIDList[i]))
                print(">>>>>>>>>>")

                currenttie = storage.tie_article_author_department(article_id, authorIDList[i], departmentIDList[i])

    else:
        bad_count+=1

# Aggregation


#Journals Targeted:
# Cell, Lancet, Nature Genetics, Public Health Nutrition, NOT!!! American Journal of Public Health
querylist = [   '?term="Cell"%5Bjour%5D&sort=date&sort_order=desc',
                '?term="Lancet+HIV"%5Bjour%5D&sort=date&sort_order=desc',
                '?term=%22Nat+Genet%22%5Bjour%5D&sort=date&sort_order=desc',
                '?sort=date&term="Public+Health+Nutr"%5Bjour%5D&sort_order=desc',
                '?term="Lancet+Public+Health"%5Bjour%5D&sort=date&sort_order=desc',
                '?term="Environ+Health+Perspect"%5Bjour%5D&sort=date&sort_order=desc',
                '?term="Lancet+Glob+Health"%5Bjour%5D&sort=date&sort_order=desc',
                '?term="BMC+Public+Health"%5Bjour%5D&sort=date&sort_order=desc',
                '?term="Euro+Surveill"%5Bjour%5D&sort=date&sort_order=desc']
                



for i in querylist:
    aggregate_by_journalquery(i, 50, 75)

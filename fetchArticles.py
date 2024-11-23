from bs4 import BeautifulSoup
import requests
from geopy.geocoders import Nominatim
import json 
# storage library for this project
import storage 

#MAPBOXTOKEN = open("mapbox.txt", "r").read().strip()
MAPBOXTOKEN = "A"
#given an article ID number, we request and parse the page. we return a json containing our data.
def getByArticleID(article_id):
    print("Getting: ", article_id)
    try:
        url = f'https://pubmed.ncbi.nlm.nih.gov/{article_id}/?format=pubmed'
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise exception for bad status codes
        
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

        # Validate required fields
        if not article_info["articleTitle"] or not article_info["journalTitle"]:
            print(f"Missing required fields for article {article_id}")
            return False

        if len(article_info["authorsList"]) != len(article_info["departmentList"]):
            print(f"Mismatch in authors/departments count for article {article_id}")
            return False

        return article_info

    except requests.RequestException as e:
        print(f"Failed to fetch article {article_id}: {str(e)}")
        return False
    except Exception as e:
        print(f"Error processing article {article_id}: {str(e)}")
        return False

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

def spoofGeo(fuzz):
    return([0.0, 0.0])

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
        latlong = spoofGeo(departmentstring)
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
                latlong = spoofGeo(new_dept_string)
                assert len(latlong) == 2
        except Exception as e2:
            print(" ?? Second exception ...")
            print(e2)
            print(latlong)
            stringlength = len(new_dept_string)
                
            new_dept_string = " ".join(new_dept_string.replace("-", " ").split(" ")[len(new_dept_string)%15:stringlength])
            print(" ? Department String Shortened for Geolocation: ", new_dept_string, "\n", "-> \n", new_dept_string)
            #new_dept_string = departmentstring[26%departmentstring:stringlength]
            latlong = spoofGeo(new_dept_string)


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
    if pages_start is None:
        pages_start = 1

    conn = storage.conn
    cursor = storage.cursor
    total_processed = 0
    total_errors = 0

    for page in range(pages_start, pages_end):
        try:
            articles_for_page = getByJournal(querystr, page)
            if not articles_for_page:
                print(f"No articles found on page {page}")
                continue

            for article_path in articles_for_page:
                # Clean and standardize the article ID
                article_id = str(article_path.replace("/","")).strip()
                if not article_id:
                    print("Empty article ID found, skipping")
                    continue

                # Check if article already exists - outside transaction
                cursor.execute('SELECT articleID FROM Articles WHERE articleID = ?', (article_id,))
                if cursor.fetchone():
                    print(f"Article {article_id} already exists, skipping")
                    continue

                # Fetch article data
                current_item = getByArticleID(int(article_id))
                if not current_item:
                    print(f"Could not fetch article {article_id}")
                    total_errors += 1
                    continue

                # Validate article data before starting transaction
                if not current_item.get('articleTitle') or not current_item.get('journalTitle'):
                    print(f"Article {article_id} missing required fields, skipping")
                    total_errors += 1
                    continue

                try:
                    # Start transaction
                    conn.execute('BEGIN')

                    # Insert article - using consistent article_id
                    storage.insert_article(
                        article_id,
                        current_item['articleTitle'],
                        current_item['journalTitle'],
                        current_item.get('datePublished', ''),  # Handle potentially missing fields
                        current_item.get('abstract', ''),
                        "<BREAKGRANT>".join(current_item.get('grantList', []))
                    )

                    author_id_list = []
                    department_id_list = []

                    # Validate authors and departments lists before processing
                    if len(current_item['authorsList']) != len(current_item['departmentList']):
                        raise ValueError(f"Mismatch in authors/departments count for article {article_id}")

                    # Process authors and departments
                    for author, department in zip(current_item['authorsList'], current_item['departmentList']):
                        if not author or not department:  # Skip empty entries
                            continue
                            
                        author_id = storage.insert_author(author.strip())
                        if author_id is None:
                            raise ValueError(f"Failed to insert author: {author}")
                        author_id_list.append(author_id)

                        extracted = CleanExtractDepartmentLocation(department)
                        if not extracted or len(extracted) != 2:
                            print(f"Invalid department data for {article_id}: {department}")
                            department_id = storage.insert_department(department.strip(), 0, 0)
                        else:
                            department_id = storage.insert_department(
                                extracted[0].strip(),
                                extracted[1][0] if extracted[1] else 0,
                                extracted[1][1] if extracted[1] else 0
                            )
                        if department_id is None:
                            raise ValueError(f"Failed to insert department: {department}")
                        department_id_list.append(department_id)

                    # Create relationships
                    for author_id, department_id in zip(author_id_list, department_id_list):
                        storage.tie_article_author_department(article_id, author_id, department_id)

                    # Commit transaction
                    conn.commit()
                    total_processed += 1
                    print(f"Successfully processed article {article_id}")

                except Exception as e:
                    print(f"Error processing article {article_id}, rolling back: {str(e)}")
                    try:
                        conn.rollback()
                    except Exception as rollback_error:
                        print(f"Rollback failed: {str(rollback_error)}")
                    total_errors += 1

        except Exception as e:
            print(f"Error processing page {page}: {str(e)}")
            try:
                conn.rollback()
            except Exception as rollback_error:
                print(f"Rollback failed: {str(rollback_error)}")
            total_errors += 1
            continue

    print(f"Aggregation complete. Processed: {total_processed}, Errors: {total_errors}")
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
                '?term="Euro+Surveill"%5Bjour%5D&sort=date&sort_order=desc',
                '?term=%22PLOS+Glob+Public+Health%22%5Bjour%5D&sort_order=desc']
                



for i in querylist:
    aggregate_by_journalquery(i, 0, 75)

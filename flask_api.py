from toolkit.db import conf, analysis, serp
from toolkit.db.conf import initialize_db, create_connection
from toolkit.graphs.core import generate_interactive_graph
from toolkit.seo.headers import find_all_headers_url
from toolkit.seo.rank import rank
from toolkit.seo.links import find_all_links
from toolkit.seo.images import find_all_images
from toolkit.seo.audit import get_all_links_website
from toolkit.seo.lighthouse import audit_google_lighthouse_full, audit_google_lighthouse_seo
from flask import Flask, request, render_template
import logging
from datetime import datetime, timedelta

# logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
#                     level=logging.DEBUG, datefmt='%m/%d/%Y %I:%M:%S %p')

app = Flask(__name__, template_folder='toolkit/templates')


@app.route('/')
def home():
    return render_template("index.html")


@app.route('/rank', methods=["POST", "GET"])
def rank_get():
    conn = create_connection("visited.db")
    error = None
    if request.method == "POST":
        query = request.form["query"]
        domain = request.form["domain"]
        result = query_domain_serp(conn, query, domain, "en", "com")
        if "limit" in result:
            error = result
        
    
    result = serp.select_query_desc(conn)
    result_list = []
    for i in result:
        result_list.append({"pos": i[2], "url": i[3], "query": i[1], "time": i[4]})
    return render_template("rank.html", result=result_list, error=error)


@app.route('/api/audit/lighthouse/full')
def audit_lighthouse_full():
    value = request.args.get('url')
    if value:
        return audit_google_lighthouse_full(value)
    else:
        return "Please input a valid value like this: /api/audit/lighthouse/full?url=https://primates.dev"


@app.route('/api/audit/lighthouse/seo')
def audit_lighthouse_seo():
    value = request.args.get('url')
    if value:
        return audit_google_lighthouse_seo(value)
    else:
        return "Please input a valid value like this: /api/audit/lighthouse/seo?url=https://primates.dev"


@app.route('/api/graph')
def interactive_graph():
    conn = create_connection("visited.db")
    with conn:
        urls = request.args.get('url')  # if key doesn't exist, returns None
        relaunch = request.args.get('redo')
        maxi_urls = request.args.get('max')
        return generate_interactive_graph(conn, urls, relaunch, maxi_urls)
    conn.close()


@app.route('/api/extract/headers')
def find_headers():
    value = request.args.get('url')
    if value:
        return find_all_headers_url(value)
    else:
        return "Please input a valid value like this: /api/extract/headers?url=https://primates.dev"


@app.route('/api/extract/links')
def find_all_links_page():
    value = request.args.get('url')
    if value:
        return find_all_links(value)
    else:
        return 'Please input a valid url like this: /api/extract/links?url=https://primates.dev'


@app.route('/api/extract/links/website')
def find_all_links_website():
    value = request.args.get('url')
    maxi = request.args.get('max')
    if value:
        if maxi:
            return get_all_links_website(value, int(maxi))
        return get_all_links_website(value)
    else:
        return 'Please input a valid url like this: /api/extract/links/website?url=https://primates.dev&max=50'


@app.route('/api/extract/images')
def find_all_images_page():
    value = request.args.get('url')
    if value:
        return find_all_images(value)
    else:
        return 'Please input a valid url like this: /api/extract/images?url=https://primates.dev'


def query_domain_serp(conn, query, domain, lang, tld):
    if query and domain:
        already = serp.select_query_already(conn, query)
        all_results = serp.select_query_desc(conn)
        if len(already) > 0:
            print(already[0])
            if datetime.strptime(already[0][4], '%m/%d/%Y, %H:%M:%S') + timedelta(hours=24) < datetime.now():
                print("refresh")
                result = rank(domain, query, lang=lang, tld=tld)
                serp.update_query(conn, (result["pos"], result["url"], datetime.now().strftime(
                    "%m/%d/%Y, %H:%M:%S"), query))
                return result
            else:
                print("no refresh")
                return {"pos": already[0][2], "url": already[0][3], "query": already[0][1]}
        if len(all_results) >= 5:
            print(len(all_results))
            print(all_results[4][4])
            if datetime.strptime(all_results[4][4], '%m/%d/%Y, %H:%M:%S') + timedelta(hours=1) > datetime.now():
                print("Already passed")
                waiting = datetime.now() - datetime.strptime(all_results[4][4], '%m/%d/%Y, %H:%M:%S')
                secs = 3600 - int(waiting.total_seconds())
                minutes = int(secs / 60) % 60
                return {"limit": "Imposing a limit of 5 query per hour to avoid Google Ban", "waiting_time": str(minutes) + "m " + str(int(secs % 60)) + "s" }   
        
        result = rank(domain, query, lang=lang, tld=tld)
        serp.insert_query_db(conn, (result["query"], result["pos"], result["url"], datetime.now().strftime(
            "%m/%d/%Y, %H:%M:%S") ))
        return result


@app.route('/api/serp')
def find_rank_query():
    conn = create_connection("visited.db")
    query = request.args.get('query')
    domain = request.args.get('domain')
    if domain and query:
        tld = request.args.get('tld')
        lang = request.args.get('lang')
        return query_domain_serp(conn,query,domain, lang, tld)
    else:
        return 'Please input a valid value like this: /api/serp?domain=primates.dev&query=parse api xml response&tld=com&lang=en'

@app.route('/api/serp/all')
def find_rank_query_all():
    conn = create_connection("visited.db")
    result = serp.select_query(conn)
    result_list = {"result":[]}
    for i in result:
        result_list["result"].append({"pos": i[2], "url": i[3], "query": i[1]})
    return result_list

@app.route('/api/analysis/keywords')
def find_keywords_query():
    conn = create_connection("visited.db")
    query = request.args.get('query')
    if query:
        return analysis.get_query_results(conn, query)

    else:
        return 'Please input a valid value like this: /api/analysis/keywords?query=parse api xml response'


if __name__ == '__main__':

    conn = create_connection("visited.db")

    if conn is not None:
        # create projects table and set running status to stopped
        initialize_db(conn)
    else:
        logging.warning("Error! cannot create the database connection.")

    logging.info("DB running")
    app.run(debug=True,host='0.0.0.0')  # run app in debug mode on port 5000

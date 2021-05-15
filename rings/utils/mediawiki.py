import asyncio
from datetime import datetime
from .utils import BotError

API_URL = 'http://tolkiengateway.net/w/api.php'
FANDOM_API_URL = "https://{sub_wikia}.fandom.com/api.php"
RATE_LIMIT = False
RATE_LIMIT_MIN_WAIT = None
RATE_LIMIT_LAST_CALL = None
USER_AGENT = 'necrobot (https://github.com/ClementJ18/necrobot)'
LANG = ""

def _check_error_response(response, query):
    """ check for default error messages and throw correct exception """
    if "error" in response:
        http_error = ["HTTP request timed out.", "Pool queue is full"]
        geo_error = [
            "Page coordinates unknown.",
            "One of the parameters gscoord, gspage, gsbbox is required",
            "Invalid coordinate provided",
        ]
        err = response["error"]["info"]
        
        if err in http_error:
            raise ValueError(query)
        if err in geo_error:
            raise ValueError(err)
        raise ValueError(err)

async def _wiki_request(self, params, fandom):
    '''
    Make a request to the Wikia API using the given search parameters.
    Returns a parsed dict of the JSON response.
    '''
    global RATE_LIMIT_LAST_CALL
    global USER_AGENT

    if fandom is not None:
        api_url = FANDOM_API_URL.format(sub_wikia=fandom)
    else:
        api_url = API_URL
    
    params['format'] = 'json'
    headers = {
        'User-Agent': USER_AGENT
    }
    
    if RATE_LIMIT and RATE_LIMIT_LAST_CALL and \
        RATE_LIMIT_LAST_CALL + RATE_LIMIT_MIN_WAIT > datetime.now():

        # it hasn't been long enough since the last API call
        # so wait until we're in the clear to make the request

        wait_time = (RATE_LIMIT_LAST_CALL + RATE_LIMIT_MIN_WAIT) - datetime.now()
        await asyncio.sleep(int(wait_time.total_seconds()))

    async with self.bot.session.get(api_url, params=params, headers=headers) as resp:
        r = await resp.json()

    if RATE_LIMIT:
        RATE_LIMIT_LAST_CALL = datetime.now()
        
    return r

async def search(self, query, fandom=None):
    search_params = {
        "action": "query",
        "generator": "search",
        "prop": "info",
        "gsrsearch": query,
    }
        
    request = await _wiki_request(self, search_params, fandom)
    _check_error_response(request, query)

    return list(request["query"]["pages"].values())
    
async def page(self, page_id, fandom=None):
    query_params = {
        "action": "query",
        "prop": "info",
        "rvprop": "content",
        "redirects": "",
        "inprop": "url",
        "rvlimit": 1,
        "rvsection": 0,
        "pageids": page_id,
    }
    
    request = await _wiki_request(self, query_params, fandom)
    _check_error_response(request, page_id)
    result = request['query']['pages'][str(page_id)]
    
    return result
    
async def parse(self, page_id, fandom=None):
    query_params = {
        "action": "parse",
        "pageid": page_id,
        "prop": "text|images",
        "section": 0,
    }

    request = await _wiki_request(self, query_params, fandom)
    _check_error_response(request, page_id)
    return request


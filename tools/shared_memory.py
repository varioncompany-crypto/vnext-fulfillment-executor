"""Cloud client. Uses HTTPS proxy/network-secret substitution; no third-party packages."""
import json
import os
import sys
import urllib.request
import urllib.error

ENDPOINT = 'https://wildlands-service.varioncompany.workers.dev/unified/memory/v1/search'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def search(query):
    token = os.environ.get('FAILSAFE_MEMORY_READ_TOKEN')
    if not token:
        raise RuntimeError('memory_network_secret_missing')
    if not query.strip() or len(query) > 1000:
        raise RuntimeError('memory_query_invalid')
    req = urllib.request.Request(ENDPOINT, data=json.dumps({'query': query}).encode(), headers={
        'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json', 'Accept': 'application/json'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=25) as response:
            raw = response.read(65537)
    except urllib.error.HTTPError as error:
        raise RuntimeError('memory_http_' + str(error.code)) from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError('memory_network_unavailable') from None
    if len(raw)>65536:
        raise RuntimeError('memory_response_too_large')
    data=json.loads(raw)
    if data.get('contract')!='failsafe.shared-memory.v1' or data.get('ok') is not True:
        raise RuntimeError('memory_read_not_confirmed')
    return data

if __name__=='__main__':
    try:
        print(json.dumps(search(' '.join(sys.argv[1:])), ensure_ascii=False, indent=2))
    except Exception as error:
        # Never print request objects, headers or credentials.
        print(json.dumps({'ok':False,'error':str(error) if isinstance(error,RuntimeError) else 'memory_client_failed'}))
        sys.exit(1)
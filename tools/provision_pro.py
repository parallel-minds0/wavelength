#!/usr/bin/env python3
"""Create/verify private Pro remote; never print credentials or push unverified visibility."""
import json,subprocess,urllib.request,urllib.error
OWNER='parallel-minds0';REPO='wavelength-pro'
def request(path,token,body=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request('https://api.github.com'+path,data=data,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'Wavelength-edition-setup','X-GitHub-Api-Version':'2022-11-28'})
    with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
def main():
    result=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,check=True)
    values=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    token=values.get('password')
    if not token:raise RuntimeError('No GitHub credential available')
    try:repo=request('/repos/'+OWNER+'/'+REPO,token)
    except urllib.error.HTTPError as error:
        if error.code!=404:raise
        user=request('/user',token)
        endpoint='/user/repos' if user['login'].lower()==OWNER.lower() else '/orgs/'+OWNER+'/repos'
        repo=request(endpoint,token,{'name':REPO,'private':True,'description':'Independent Wavelength Pro source tree'})
    if not repo.get('private') or repo.get('visibility')!='private':raise RuntimeError('Pro repository is not private; refusing publication')
    print(json.dumps({'repository':repo['full_name'],'visibility':repo['visibility'],'url':repo['html_url']}))
if __name__=='__main__':main()

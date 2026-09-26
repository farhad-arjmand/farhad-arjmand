"""Generate profile cards from explicitly public GitHub data only."""
import datetime
import html
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request

USER = 'farhad-arjmand'

def api(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'public-profile-cards'}
    if os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    with urllib.request.urlopen(urllib.request.Request('https://api.github.com/' + path, headers=headers), timeout=30) as response:
        return json.load(response)

repos = []
page = 1
while True:
    batch = api(f'users/{USER}/repos?type=owner&per_page=100&page={page}')
    repos.extend(r for r in batch if not r['private'])
    if len(batch) < 100:
        break
    page += 1
owned = [r for r in repos if not r['fork']]
commits = api('search/commits?' + urllib.parse.urlencode({'q': f'author:{USER} is:public', 'per_page': 1}))
prs = api('search/issues?' + urllib.parse.urlencode({'q': f'author:{USER} type:pr is:public', 'per_page': 1}))
if commits.get('incomplete_results') or prs.get('incomplete_results'):
    raise RuntimeError('GitHub returned incomplete search results; preserve previous cards')
languages = {}
for repo in owned:
    if repo['name'].lower() == USER:
        continue  # Profile SVGs are decoration, not a programming-language sample.
    for language, size in api(f'repos/{USER}/{repo["name"]}/languages').items():
        languages[language] = languages.get(language, 0) + size

stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')

def text(x,y,value,size=16,color='#a5f3fc',weight='400'):
    return f'<text x="{x}" y="{y}" fill="{color}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" font-weight="{weight}">{html.escape(str(value))}</text>'
def card(title, content, desc):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="495" height="245" viewBox="0 0 495 245" role="img"><title>{html.escape(title)}</title><desc>{html.escape(desc)}</desc><rect x="1" y="1" width="493" height="243" rx="14" fill="#141321" stroke="#40445c"/>' + text(24,38,title,22,'#ff4d9d','700') + content + text(24,226,'Public data · updated '+stamp,11,'#94a3b8') + '</svg>'

rows = [('Stars on owned public repos', sum(r['stargazers_count'] for r in owned)), ('Indexed public commits',commits['total_count']),('Public pull requests',prs['total_count']),('Public repositories',len(repos))]
stats = ''.join(text(25,77+i*36,label,16) + text(427,77+i*36,value,21,'#e2e8f0','700') for i,(label,value) in enumerate(rows))
colors={'PHP':'#a78bfa','TypeScript':'#3178c6','JavaScript':'#f1e05a','Vue':'#41b883','HTML':'#e34c26','CSS':'#b291f1','Dockerfile':'#38bdf8','Go':'#00add8'}
ordered=sorted(languages.items(), key=lambda x:x[1],reverse=True)
if len(ordered)>6:
    ordered=ordered[:5]+[('Other',sum(n for _,n in ordered[5:]))]
total=sum(n for _,n in ordered)
content=''; x=24
for name,size in ordered:
    width=447*size/total
    content+=f'<rect x="{x:.2f}" y="61" width="{width:.2f}" height="13" fill="{colors.get(name,"#94a3b8")}"/>'
    x+=width
for i,(name,size) in enumerate(ordered):
    x=24+(i%2)*234; y=110+(i//2)*33
    content+=f'<circle cx="{x+5}" cy="{y-5}" r="5" fill="{colors.get(name,"#94a3b8")}"/>'+text(x+18,y,f'{name} {size/total:.1%}',13)
content+=text(24,199,'Owned public code · forks & profile excluded',11,'#94a3b8')
out=Path(__file__).resolve().parents[1]/'assets'
out.mkdir(exist_ok=True)
(out/'github-stats.svg').write_text(card('My GitHub Statistics',stats,'Public GitHub counts. Commits use GitHub public commit search, not a lifetime or private-work total.'))
(out/'languages.svg').write_text(card('Languages in My Public Code',content,'Language distribution by bytes in owned public repositories; not a skill rating.'))
print('Generated public stats and language cards:', dict(rows),languages)

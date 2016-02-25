from flask import Flask, render_template,request,jsonify
from lxml import etree
import requests
import re

import logging
from logging.handlers import RotatingFileHandler

import json

app = Flask(__name__)

@app.route('/<game_class>')
def lookup(game_class):
    # preload data
    cards = load_data(game_class)
    return render_template('lookup.html', game_class = game_class)

@app.route('/lookupcard/<game_class>', methods=['GET'])
def lookupcard(game_class):
    
    pattern = request.args.get("cardpattern")

    cards = load_data(game_class)
 
    for card in cards:
        if pattern.lower() in card.lower():
            return jsonify({'html': render_template('card.html', card=card, stats=cards[card], imgurl=get_hearthpwn_imgurl(cards[card]['url'])) })

    return jsonify({'html': render_template('cardnotfound.html')})

def load_data(game_class):

    # Try to load local data
    try:
        with open( get_data_filename(game_class) ) as f:
            cards = json.load( f )
            app.logger.info("Local data loaded for class '{}'.".format(game_class))
    # In case of failure get new remote data
    except EnvironmentError as e:
        app.logger.info("Error reading local file for class '{}': '{}'.".format(game_class,e))
    except ValueError as e:
        app.logger.info("Error parsing json for class '{}': '{}'.".format(game_class,e))
    finally:
        cards = get_remote_data(game_class)
    return cards


def get_remote_data(game_class):
    
    url = "http://www.icy-veins.com/hearthstone/arena-{}-tier-lists-league-of-explorers".format(game_class)
    
    r = requests.get(url);
    
    html = etree.HTML(r.content)

    cards  = {}

    # <table id="arena_spreadsheet_table_<rarity>">
    #   <tr><th>Tier 1: Excellent</th></tr>
    #   <tr>
    #     <td><a>Drakonid Crusher</a></td>
    #   </tr>
    # </table>

    for rarity in ['common', 'rare', 'epic', 'legendary']:

        tbl = html.xpath( "//table[@id='arena_spreadsheet_table_{}']".format(rarity) )

        for tr in tbl[0].iter('tr'):
        
            for tr_child in tr.findall("./"):
            
                if tr_child.tag == 'th':
                    tier = tr_child.text[8:]
                    continue

                card_links = tr_child.xpath('a')
            
                if card_links:
                    cardurl = card_links[0].get('data-tooltip-href')
                    cards[card_links[0].text] = {'rarity': rarity, 'tier': tier, 'url': cardurl}

    with open(get_data_filename(game_class), "w") as outfile:
            json.dump(cards, outfile, indent=4)
    
    return cards

def get_hearthpwn_imgurl(cardurl):
    r = requests.get("{}/tooltip".format(cardurl))
    m = re.search(r"http://media-Hearth.cursecdn.com/avatars/[0-9]+/[0-9]+/[0-9]+.png", r.content)
    return m.group(0)
    
def get_data_filename(game_class):
    return "{}-data.json".format(game_class)

if __name__ == "__main__":
    handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.run(debug=True)



import json, subprocess, datetime

CDN = "https://photos.zillowstatic.com/fp/"
PHOTOS_BASE = "photos/"

# Map from old b64 key to local image filename
B64_FILES = {
    "4":  "1335-fortuna-ave.jpg",
    "5":  "56367-scandia-ln.jpg",
    "6":  "8500-samel-rd.jpg",
    "7":  "1224-shangri-la-rd.jpg",
    "8":  "4650-sizer-canyon-rd.jpg",
    "9":  "7276-encina-rd.jpg",
    "10": "877-e-phillips-rd.jpg",
    "11": "63300-tilford-way.jpg",
    "12": "2351-n-cambria-ave.jpg",
}

def b64(k): return f"{PHOTOS_BASE}{B64_FILES[k]}"
def zillow_img(h): return f"{CDN}{h}-cc_ft_1536.jpg"

def zillow_url(addr):
    a = addr.replace(',','').replace(' ','-').replace('--','-')
    return f"https://www.zillow.com/homes/{a}_rb/"

LATLNG = {
    "1335 Fortuna Ave, Landers, CA 92285": (34.274045, -116.426363),
    "56367 Scandia Ln, Yucca Valley, CA 92284": (34.195217, -116.432860),
    "8500 S Samel Rd, Morongo Valley, CA 92256": (34.097905, -116.511178),
    "1224 Shangri La Rd, Joshua Tree, CA 92252": (34.231430, -116.323253),
    "4650 Sizer Canyon Rd, Johnson Valley, CA 92285": (34.334711, -116.553058),
    "7276 Encina Rd, Joshua Tree, CA 92252": (34.120662, -116.324009),
    "877 E Phillips Rd, Landers, CA 92285": (34.265415, -116.325323),
    "63300 Tilford Way, Joshua Tree, CA 92252": (34.213345, -116.281674),
    "2351 N Cambria Ave, Landers, CA 92285": (34.291757, -116.430646),
    "50740 Santa Rosa Plz APT 2, La Quinta, CA 92253": (33.679208, -116.302189),
    "4537 Anita Ave, Yucca Valley, CA 92284": (34.170580, -116.367336),
    "69450 Amboy Rd, Twentynine Palms, CA 92277": (34.164160, -116.148522),
    "376 Riverside Ave, Sugarloaf, CA 92386": (34.245452, -116.834467),
    "396 Kern Ave, Sugarloaf, CA 92386": (34.244957, -116.835238),
    "697 Villa Grove Ave, Big Bear City, CA 92314": (34.238971, -116.855846),
    "346 San Bernardino Ave, Sugarloaf, CA 92386": (34.246000, -116.833860),
    "446 Riverside Ave, Sugarloaf, CA 92386": (34.244053, -116.834633),
    "1388 Jemez Trl, Landers, CA 92285": (34.273390, -116.454986),
    "57920 Buena Vista Dr, Yucca Valley, CA 92284": (34.164106, -116.399646),
    "2088 Acoma Trl, Landers, CA 92285": (34.287326, -116.439652),
    "60654 Mitch Ln, Landers, CA 92285": (34.280575, -116.338752),
    "8729 Rockhaven Rd, Joshua Tree, CA 92252": (34.095479, -116.268885),
    "72767 Mesquite Dunes Rd, Twentynine Palms, CA 92277": (34.210884, -116.073092),
    "55921 Ornelas Ln, Landers, CA 92285": (34.292666, -116.443584),
    "290 Bluegrass Rd, Twentynine Palms, CA 92277": (34.248055, -116.128342),
    "1564 Luna Mesa Rd, Yucca Valley, CA 92284": (34.224156, -116.391249),
}

def fmt_money(v):
    if v is None: return "N/A"
    neg = v < 0
    s = f"${abs(v):,.0f}"
    return f"-{s}" if neg else f"+{s}"

def fmt_plain(v):
    if v is None: return "N/A"
    return f"${abs(v):,.0f}"

def compute(price, annual_rev, piti_30, down_30, sqft, has_pool=False):
    furnishing = sqft * 16
    buyer_agent = price * 0.025
    closing = price * 0.02
    startup = down_30 + furnishing + buyer_agent + closing
    if not annual_rev or annual_rev <= 0:
        return {"mo_rev":0,"piti":piti_30,"cleaning":0,"pool":250 if has_pool else 0,
                "cf":None,"coc":None,"down":down_30,"furnishing":furnishing,
                "buyer_agent":buyer_agent,"closing":closing,"startup":startup,
                "annual_rev":annual_rev or 0,"no_rev":True}
    mo = annual_rev / 12
    cl = mo * 0.23
    po = 250 if has_pool else 0
    cf = mo - piti_30 - cl - po
    coc = (cf * 12) / startup * 100 if startup > 0 else 0
    return {"mo_rev":mo,"piti":piti_30,"cleaning":cl,"pool":po,
            "cf":cf,"coc":coc,"down":down_30,"furnishing":furnishing,
            "buyer_agent":buyer_agent,"closing":closing,"startup":startup,
            "annual_rev":annual_rev,"no_rev":False}

def card(p, show_source=None):
    f = p.get("fin")
    addr_parts = p["address"].split(",", 1)
    street = addr_parts[0]
    city_state = addr_parts[1].strip() if len(addr_parts) > 1 else ""
    zillow_link = p.get("zillow_link") or zillow_url(p["address"])
    airbnb_link = p.get("airbnb_link", "")
    img_src = p.get("img_src", "")
    img_tag = f'<img src="{img_src}" alt="{street}" onerror="this.style.display=\'none\';this.parentNode.classList.add(\'img-fallback\')">' if img_src else ''
    if p.get("original_price") and p.get("price") and p["original_price"] > p["price"]:
        price_fmt = f'<del>${p["original_price"]:,}</del> ${p["price"]:,}'
    else:
        price_fmt = f"${p['price']:,}" if p.get('price') else ""

    chips_html = ""
    if p.get("beds"): chips_html += f'<span class="chip chip-bed">{p["beds"]} bd</span>'
    if p.get("baths"): chips_html += f'<span class="chip chip-bath">{p["baths"]} ba</span>'
    if p.get("sqft"): chips_html += f'<span class="chip chip-sqft">{p["sqft"]:,} sqft</span>'
    if p.get("region"): chips_html += f'<span class="chip chip-region">{p["region"]}</span>'
    if show_source: chips_html += f'<span class="chip chip-source">{show_source}</span>'
    dom = p.get("dom")
    if dom is not None:
        if dom <= 30: dom_cls = "chip-dom-green"
        elif dom <= 60: dom_cls = "chip-dom-yellow"
        else: dom_cls = "chip-dom-red"
        chips_html += f'<span class="chip {dom_cls}" title="Days on Market">📅 {dom}d</span>'

    da = ""
    if f:
        da = f' data-annual-rev="{f["annual_rev"]}" data-piti="{f["piti"]:.4f}" data-pool="{f["pool"]}" data-base-startup="{f["startup"]:.4f}"'

    if f and not f.get("no_rev"):
        mo_rev = f["mo_rev"]
        cf = f["cf"]
        cf_class = "positive" if cf >= 0 else "negative"
        cash_rows = f'''
          <div class="cost-row"><span class="label">Mo. Revenue</span><span class="amount neutral mo-rev-val">+{fmt_plain(mo_rev)}/mo</span></div>
          <div class="cost-row"><span class="label">PITI (mtg+tax+ins)</span><span class="amount negative">-{fmt_plain(f["piti"])}/mo</span></div>
          <div class="cost-row"><span class="label">Cleaning (23%)</span><span class="amount negative cleaning-val">-{fmt_plain(f["cleaning"])}/mo</span></div>'''
        if f["pool"]:
            cash_rows += '\n          <div class="cost-row"><span class="label">Pool service</span><span class="amount negative">-$250/mo</span></div>'
        cash_rows += f'\n          <div class="cost-row total-row"><span class="label">Net Cash Flow</span><span class="amount {cf_class} net-cf-val">{fmt_money(cf)}/mo</span></div>'
        cost_html = f'<div class="cost-breakdown">{cash_rows}\n        </div>'

        coc = f["coc"]
        bar_width = max(0, min(100, (min(max(coc,-20),50)+20)/70*100))
        bar_color = "#22c55e" if coc >= 0 else "#ef4444"
        coc_html = f'''<div class="coc-section">
          <div class="coc-label">Cash-on-Cash Return</div>
          <div class="coc-bar-wrap"><div class="coc-bar" style="width:{bar_width:.1f}%;background:{bar_color}"></div></div>
          <div class="coc-value {'coc-positive' if coc>=0 else 'coc-negative'}">{coc:+.1f}%</div>
        </div>'''

        rev_src = p.get("rev_source", "AirROI est.")
        rev_html = f'''<div class="rev-adjust">
          <div class="rev-adjust-header">
            <span class="rev-adjust-title">📊 Revenue Assumption</span>
            <span class="rev-tag">{rev_src}</span>
          </div>
          <div class="rev-adjust-row">
            <span>Annual Revenue</span>
            <input type="text" class="rev-input" value="{int(f['annual_rev']):,}" oninput="recalcCard(this)" onclick="this.select()">
          </div>
          {f'<div class="rev-adjust-row comp-avg-row"><span>Comp avg</span><span>{p["comp_avg"]["occ"]:.0f}% occ · ${p["comp_avg"]["adr"]:,.0f} ADR</span></div>' if p.get("comp_avg") else ""}
        </div>'''
    else:
        cost_html = '<div class="cost-breakdown"><p class="no-data-msg">Revenue data not yet available</p></div>'
        coc_html = '<div class="coc-section"><span class="coc-label">Cash-on-Cash Return</span><span class="coc-value coc-na" style="margin-left:auto">N/A</span></div>'
        rev_html = ''

    if f:
        startup_html = f'''<div class="startup-section">
          <div class="startup-title">Startup Costs</div>
          <div class="startup-row"><span>Down Payment (30%)</span><span>{fmt_plain(f["down"])}</span></div>
          <div class="startup-row"><span>Furnishing ($16/sqft)</span><span>{fmt_plain(f["furnishing"])}</span></div>
          <div class="startup-row"><span>Buyer\'s Agent (2.5%)</span><span>{fmt_plain(f["buyer_agent"])}</span></div>
          <div class="startup-row"><span>Closing Costs (est. 2%)</span><span>{fmt_plain(f["closing"])}</span></div>
          <div class="startup-row remodel-row">
            <span>Remodel Budget</span>
            <input type="text" class="remodel-input" placeholder="$0" oninput="recalcCard(this)">
          </div>
          <div class="startup-row startup-total"><span>Total Cash In</span><span class="startup-total-val">{fmt_plain(f["startup"])}</span></div>
        </div>'''
    else:
        startup_html = ""

    coc_val = f["coc"] if f else None
    if p.get("sold"): card_class = "property-card card-sold"
    elif coc_val is not None and coc_val > 0: card_class = "property-card card-green"
    elif coc_val is not None and coc_val < 0: card_class = "property-card card-red"
    else: card_class = "property-card"

    sold_html = '<div class="sold-overlay">SOLD</div>' if p.get("sold") else ""

    links_html = f'<a href="{zillow_link}" target="_blank" class="listing-btn zillow-btn">🏠 Zillow</a>'
    if airbnb_link and airbnb_link.startswith("http"):
        links_html += f'<a href="{airbnb_link}" target="_blank" class="listing-btn airbnb-btn">📍 AirBnB</a>'

    comps_html = ""
    if p.get("comps"):
        strips = "".join(
            f'<a href="{c["url"]}" target="_blank" class="comp-strip" title="{c["name"]}">'
            f'<span>{c["occ"]:.0f}% occ</span><span>${c["adr"]:,.0f} ADR</span><span>${c["annual_rev"]/1000:.1f}K/yr</span><span class="cs-arrow">↗</span></a>'
            for c in p["comps"])
        comps_html = f'<div class="comp-strips"><div class="comp-strips-title">Comps ({len(p["comps"])})</div>{strips}</div>'

    _ll = LATLNG.get(p["address"])
    ll_attr = f' data-lat="{_ll[0]}" data-lng="{_ll[1]}"' if _ll else ''
    return f'''<div class="{card_class}" data-addr="{p["address"]}"{ll_attr}{da}>
      <div class="card-image{'' if img_src else ' img-fallback'}">
        {img_tag}
        <div class="price-badge">{price_fmt}</div>
        <button class="fav-btn" onclick="toggleFav(this)" title="Favorite">♥</button>
        {sold_html}
      </div>
      <div class="card-body">
        <div class="card-address">{street}</div>
        <div class="card-city">{city_state}</div>
        <div class="card-chips">{chips_html}</div>
        {cost_html}
        {coc_html}
        {rev_html}
        {startup_html}
        <div class="card-links">{links_html}</div>
        {comps_html}
      </div>
    </div>'''

def comp_card(p):
    addr_parts = p["address"].split(",", 1)
    street = addr_parts[0]; city_state = addr_parts[1].strip() if len(addr_parts)>1 else ""
    occ_pct = p.get("occ",0)*100; rev=p.get("annual_rev",0); adr=p.get("adr",0)
    listing_name=p.get("listing_name",""); notes=p.get("notes","")
    return f'''<div class="comp-card">
      <div class="comp-header">
        <div class="comp-address">{street}</div>
        <div class="comp-city">{city_state}</div>
        {f'<div class="comp-listing-name">{listing_name}</div>' if listing_name else ""}
      </div>
      <div class="comp-metrics">
        <div class="comp-metric"><span class="cm-label">Annual Revenue</span><span class="cm-value green">${rev:,}</span></div>
        <div class="comp-metric"><span class="cm-label">ADR</span><span class="cm-value">${adr}</span></div>
        <div class="comp-metric"><span class="cm-label">Occupancy</span><span class="cm-value">{occ_pct:.0f}%</span></div>
        <div class="comp-metric"><span class="cm-label">Rating</span><span class="cm-value">⭐ {p.get("rating","")}</span></div>
        <div class="comp-metric"><span class="cm-label">Reviews</span><span class="cm-value">{p.get("reviews","")}</span></div>
        <div class="comp-metric"><span class="cm-label">Mo. Revenue</span><span class="cm-value green">${rev//12:,}</span></div>
      </div>
      <div class="occ-bar-wrap"><div class="occ-bar" style="width:{min(100,occ_pct):.1f}%;background:#f97316"></div></div>
      {f'<div class="comp-notes">{notes}</div>' if notes else ""}
      <div class="card-links"><a href="{p.get("airbnb_link","#")}" target="_blank" class="listing-btn airbnb-btn">📍 View Listing</a></div>
    </div>'''

def tab_section(tab_id, title, properties_list, is_comp=False, show_sources=False):
    if is_comp:
        cards_html = "\n    ".join(comp_card(p) for p in properties_list)
        grid_class = "comp-grid"
    else:
        if show_sources:
            cards_html = "\n    ".join(card(p, show_source=p.get('_source')) for p in properties_list)
        else:
            cards_html = "\n    ".join(card(p) for p in properties_list)
        grid_class = "cards-grid"
    return f'''  <div id="tab-{tab_id}" class="tab-content" style="display:none">
    <div class="tab-header">
      <h2>{title}</h2>
      <span class="prop-count">{len(properties_list)} properties</span>
    </div>
    <div class="{grid_class}">
    {cards_html}
    </div>
  </div>'''

PH = ""

only_tab = [
    {"address":"1335 Fortuna Ave, Landers, CA 92285","region":"Landers","price":375000,"beds":2,"baths":1,"sqft":952,"dom":110,"img_src":b64("4"),"fin":compute(375000,4863.63,2337.42,112500,952)},
    {"address":"56367 Scandia Ln, Yucca Valley, CA 92284","region":"Yucca Valley","price":510000,"beds":1,"baths":2,"sqft":994,"dom":763,"img_src":b64("5"),"fin":compute(510000,0,3106.13,153000,994)},
    {"address":"8500 S Samel Rd, Morongo Valley, CA 92256","region":"Morongo Valley","price":440000,"beds":1,"baths":1,"sqft":936,"img_src":b64("6"),"airbnb_link":"https://www.airbnb.com/rooms/1096561622451349502","fin":compute(440000,81500,2707.13,132000,936)},
    {"address":"1224 Shangri La Rd, Joshua Tree, CA 92252","region":"Joshua Tree","price":325000,"beds":1,"baths":1,"sqft":1937,"img_src":b64("7"),"fin":compute(325000,0,2052.56,97500,1937)},
    {"address":"4650 Sizer Canyon Rd, Johnson Valley, CA 92285","region":"Johnson Valley","price":440000,"beds":2,"baths":1,"sqft":947,"dom":254,"img_src":b64("8"),"fin":compute(440000,36800,2707.13,132000,947)},
    {"address":"7276 Encina Rd, Joshua Tree, CA 92252","region":"Joshua Tree","price":374900,"original_price":399000,"beds":1,"baths":1,"sqft":662,"dom":118,"img_src":b64("9"),"zillow_link":"https://www.zillow.com/homedetails/7276-Encina-Rd-Joshua-Tree-CA-92252/337970717_zpid/","airbnb_link":"https://www.airbnb.com/rooms/971911711973779101","fin":compute(374900,62600,2336.95,112470,662)},
    {"address":"877 E Phillips Rd, Landers, CA 92285","region":"Landers","price":299000,"original_price":369000,"beds":1,"baths":1,"sqft":690,"dom":465,"img_src":b64("10"),"zillow_link":"https://www.zillow.com/homedetails/877-E-Phillips-Rd-Landers-CA-92285/17508176_zpid/","fin":compute(299000,26200,1903.48,89700,690)},
    {"address":"63300 Tilford Way, Joshua Tree, CA 92252","region":"Joshua Tree","price":399000,"beds":1,"baths":1,"sqft":900,"dom":1,"img_src":b64("11"),"zillow_link":"https://www.zillow.com/homedetails/63300-Tilford-Way-Joshua-Tree-CA-92252/17508509_zpid/","fin":compute(399000,90789.37,2474.19,119700,900,has_pool=True)},
    {"address":"2351 N Cambria Ave, Landers, CA 92285","region":"Landers","price":499000,"beds":3,"baths":2,"sqft":1467,"dom":6,"img_src":b64("12"),"zillow_link":"https://www.zillow.com/homedetails/2351-N-Cambria-Ave-Landers-CA-92285/463469847_zpid/","fin":compute(499000,94280.23,3043.90,149700,1467,has_pool=True)},
]
only_tab.sort(key=lambda p: p["fin"]["coc"] if p["fin"].get("coc") is not None else -999, reverse=True)

laquinta_tab = [
    {"address":"50740 Santa Rosa Plz APT 2, La Quinta, CA 92253","region":"La Quinta","price":315000,"beds":1,"baths":1,"sqft":682,"img_src":zillow_img("dbac82a7b26bc71760fc21cac9d4c4e2"),"airbnb_link":"https://www.airbnb.com/rooms/748771224286105523","fin":compute(315000,28400,1994.99,94500,682)},
]

duplex_tab = [
    {"address":"4537 Anita Ave, Yucca Valley, CA 92284","region":"Morongo","price":620000,"beds":6,"baths":3,"sqft":2965,"img_src":zillow_img("abbeb38ee830ad6682c5095ca7fdeb68"),"fin":compute(620000,53500,3733.41,186000,2965)},
    {"address":"56367 Scandia Ln, Yucca Valley, CA 92284","region":"Morongo","price":510000,"beds":1,"baths":2,"sqft":994,"dom":763,"img_src":b64("5"),"fin":compute(510000,0,3106.13,153000,994)},
    {"address":"69450 Amboy Rd, Twentynine Palms, CA 92277","region":"29 Palms","price":599000,"beds":4,"baths":2,"sqft":1303,"img_src":zillow_img("61b95dfdcdc15b9a01b143800fa70b97"),"airbnb_link":"https://www.airbnb.com/rooms/769512618474065409","fin":compute(599000,103600,3613.61,179700,1303)},
]

bigbear_tab = [
    {"address":"376 Riverside Ave, Sugarloaf, CA 92386","region":"Big Bear","price":259900,"beds":1,"baths":1,"sqft":504,"img_src":"photos/376-riverside-ave.png","fin":compute(259900,19700,1681.38,77970,504)},
    {"address":"396 Kern Ave, Sugarloaf, CA 92386","region":"Big Bear","price":299999,"beds":2,"baths":1,"sqft":720,"img_src":"photos/396-kern-ave.jpg","zillow_link":"https://www.zillow.com/homedetails/396-Kern-Ave-Sugarloaf-CA-92386/17621919_zpid/","airbnb_link":"https://www.airbnb.com/rooms/769657678133226978","fin":compute(299999,19000,1909.13,89999,720)},
    {"address":"697 Villa Grove Ave, Big Bear City, CA 92314","region":"Big Bear","price":299900,"beds":2,"baths":1,"sqft":750,"dom":53,"img_src":zillow_img("58a1652c34b769e0b9521cd7ab9c77fd"),"zillow_link":"https://www.zillow.com/homedetails/697-Villa-Grove-Ave-Big-Bear-City-CA-92314/17621284_zpid/","fin":compute(299900,44500,1908.67,89970,750)},
    {"address":"346 San Bernardino Ave, Sugarloaf, CA 92386","region":"Big Bear","price":285000,"original_price":295000,"beds":2,"baths":1,"sqft":608,"dom":161,"img_src":zillow_img("06724d0ccfa7d6dce1c83230eb026a58"),"zillow_link":"https://www.zillow.com/homedetails/346-San-Bernardino-Ave-Sugarloaf-CA-92386/2070283678_zpid/","fin":compute(285000,44200,1824.44,85500,608)},
]

sold_tab = [
    {"address":"446 Riverside Ave, Sugarloaf, CA 92386","region":"Big Bear","price":309000,"beds":1,"baths":1,"sqft":573,"sold":True,"img_src":PH,"fin":compute(309000,19700,1961.05,92700,573)},
]

adu_tab = [
    {"address":"1388 Jemez Trl, Landers, CA 92285","region":"Landers","price":499999,"beds":3,"baths":3,"sqft":3120,"dom":238,"img_src":zillow_img("90fd67edf07a47ca04f3171349739389"),"fin":compute(499999,0,3049.55,149999,3120)},
    {"address":"57920 Buena Vista Dr, Yucca Valley, CA 92284","region":"Yucca Valley","price":475000,"beds":3,"baths":2,"sqft":1600,"img_src":zillow_img("f0422669224f64ea639fda4d2c808777"),"airbnb_link":"https://www.airbnb.com/rooms/930306660730554905","fin":compute(475000,35900,2907.13,142500,1600)},
]

competition_tab = [
    {"address":"2088 Acoma Trl, Landers, CA 92285","region":"Landers","price":316500,"beds":2,"baths":1,"sqft":858,"img_src":zillow_img("0e09564c766053b1b8ddff1d9e18ff4c"),"airbnb_link":"https://www.airbnb.com/rooms/49210867","rev_source":"Airbnb verified","fin":compute(316500,57500,2003.98,94950,858,has_pool=True)},
]

money_tab = [
    {"address":"60654 Mitch Ln, Landers, CA 92285","region":"Landers","price":365000,"original_price":385000,"beds":1,"baths":1,"sqft":448,"dom":72,"img_src":zillow_img("085bad920e162f8a6d0146a5585f2efa"),"zillow_link":"https://www.zillow.com/homedetails/60654-Mitch-Ln-Landers-CA-92285/299170864_zpid/","airbnb_link":"https://www.airbnb.com/rooms/647212501055315908","rev_source":"Airbnb verified","fin":compute(365000,71300,2274.74,109500,448)},
    {"address":"69450 Amboy Rd, Twentynine Palms, CA 92277","region":"29 Palms","price":599000,"beds":4,"baths":2,"sqft":1303,"img_src":zillow_img("61b95dfdcdc15b9a01b143800fa70b97"),"airbnb_link":"https://www.airbnb.com/rooms/769512618474065409","fin":compute(599000,80232,3613.61,179700,1303)},
    {"address":"7276 Encina Rd, Joshua Tree, CA 92252","region":"Joshua Tree","price":374900,"original_price":399000,"beds":1,"baths":1,"sqft":662,"dom":118,"img_src":b64("9"),"zillow_link":"https://www.zillow.com/homedetails/7276-Encina-Rd-Joshua-Tree-CA-92252/337970717_zpid/","airbnb_link":"https://www.airbnb.com/rooms/971911711973779101","fin":compute(374900,52364,2336.95,112470,662)},
    {"address":"8729 Rockhaven Rd, Joshua Tree, CA 92252","region":"Joshua Tree","price":710000,"beds":1,"baths":1,"sqft":968,"img_src":zillow_img("458814cc0ce69e2a1400231a7d78aac1"),"airbnb_link":"https://www.airbnb.com/rooms/603759782385162711","fin":compute(710000,107332,4246.55,213000,968)},
    {"address":"72767 Mesquite Dunes Rd, Twentynine Palms, CA 92277","region":"29 Palms","price":599000,"beds":2,"baths":1,"sqft":1094,"img_src":zillow_img("814e00f87608b29e697cd736fa6f9baa"),"airbnb_link":"https://www.airbnb.com/rooms/49347365","fin":compute(599000,75000,3613.61,179700,1094)},
    {"address":"55921 Ornelas Ln, Landers, CA 92285","region":"Landers","price":349000,"beds":2,"baths":2,"sqft":976,"dom":126,"img_src":zillow_img("ecc9f6617ce31a3f847e31005f94a436"),"zillow_link":"https://www.zillow.com/homedetails/55921-Ornelas-Ln-Landers-CA-92285/17507410_zpid/","airbnb_link":"https://www.airbnb.com/rooms/48836260","fin":compute(349000,42219,2189.33,104700,976)},
    {"address":"290 Bluegrass Rd, Twentynine Palms, CA 92277","region":"29 Palms","price":359000,"beds":3,"baths":1,"sqft":1451,"img_src":zillow_img("8d3178634371ed1fcfc9df50fbac384f"),"airbnb_link":"https://www.airbnb.com/rooms/38159960","fin":compute(359000,51387,2245.91,107700,1451)},
    {"address":"1564 Luna Mesa Rd, Yucca Valley, CA 92284","region":"Yucca Valley","price":498000,"beds":2,"baths":2,"sqft":792,"dom":47,"img_src":zillow_img("b80decd558b9a98a713ea98e760ef422"),"zillow_link":"https://www.zillow.com/homedetails/1564-Luna-Mesa-Rd-Yucca-Valley-CA-92284/17508241_zpid/","airbnb_link":"https://www.airbnb.com/rooms/45222274","fin":compute(498000,77000,3038.24,149400,792)},
    {"address":"2351 N Cambria Ave, Landers, CA 92285","region":"Landers","price":499000,"beds":3,"baths":2,"sqft":1467,"dom":6,"img_src":b64("12"),"zillow_link":"https://www.zillow.com/homedetails/2351-N-Cambria-Ave-Landers-CA-92285/463469847_zpid/","fin":compute(499000,109600,3043.90,149700,1467,has_pool=True)},
]

# ---- Comps: per-property Airbnb comps. Averages drive the property's revenue assumption. ----
COMPS = {
    "63300 Tilford Way, Joshua Tree, CA 92252": [
        {"name":"Romantic Cabin, Sweeping Views, Spa · Stone Hill","url":"https://www.airbnb.com/rooms/1050251825957778903","annual_rev":117900,"adr":360,"occ":83.8},
        {"name":"Casa Lenta · Romantic Retreat w/ Pool, Spa, Views","url":"https://www.airbnb.com/rooms/583294576342371719","annual_rev":99100,"adr":338,"occ":69.9},
        {"name":"CouplesPool, Spa&Tub | Bikes | Telescope | Theater","url":"https://www.airbnb.com/rooms/1313828204666358101","annual_rev":84300,"adr":291,"occ":69.0},
        {"name":"DTJT House 2 - SWIM, SOAK & STARGAZE","url":"https://www.airbnb.com/rooms/45829660","annual_rev":62000,"adr":245,"occ":58.1},
    ],
}

def apply_comps(tabs):
    seen = set()
    for tab in tabs:
        for p in tab:
            comps = COMPS.get(p["address"])
            if not comps or id(p) in seen:
                continue
            seen.add(id(p))
            n = len(comps)
            avg_rev = sum(c["annual_rev"] for c in comps) / n
            p["comps"] = comps
            p["comp_avg"] = {"adr": sum(c["adr"] for c in comps)/n, "occ": sum(c["occ"] for c in comps)/n}
            p["rev_source"] = f"Avg of {n} comps"
            f0 = p["fin"]
            p["fin"] = compute(p["price"], avg_rev, f0["piti"], f0["down"], p["sqft"], has_pool=f0["pool"] > 0)

apply_comps([only_tab, laquinta_tab, duplex_tab, bigbear_tab, sold_tab, adu_tab, money_tab])

money_tab.sort(key=lambda p: p["fin"]["coc"] if p["fin"].get("coc") is not None else -999, reverse=True)
adu_tab.extend(duplex_tab)

# Favorites seeds live on their natural region tab; hearts move them at runtime
FAV_DEFAULT_ADDRS = [p["address"] for p in only_tab]
for _p in only_tab:
    _target = bigbear_tab if ("Sugarloaf" in _p["address"] or "Big Bear" in _p["address"] or _p.get("region")=="Big Bear") else money_tab
    if not any(q["address"] == _p["address"] for q in _target):
        _target.append(_p)
money_tab.sort(key=lambda p: p["fin"]["coc"] if p["fin"].get("coc") is not None else -999, reverse=True)

for _t in (laquinta_tab, bigbear_tab, adu_tab, sold_tab):
    _t.sort(key=lambda p: p["fin"]["coc"] if p["fin"].get("coc") is not None else -999, reverse=True)

comp_tracker = [
    {"address":"3979 Dusty Mile Rd, Landers, CA 92285","listing_name":"Escape and Rejuvenate at K.B.'s Desert Cabin","annual_rev":20500,"adr":149,"occ":0.315,"rating":4.9,"reviews":195,"airbnb_link":"https://www.airbnb.com/rooms/24018672","notes":""},
    {"address":"55125 Gleason Rd, Landers, CA 92285","listing_name":"Arcturus Landing - The brightest star in the desert","annual_rev":29700,"adr":152,"occ":0.474,"rating":5.0,"reviews":491,"airbnb_link":"https://www.airbnb.com/rooms/43863206","notes":""},
    {"address":"GPS: 34.30113, -116.42657 (unlisted)","listing_name":"Watermelon Sugar, Joshua Tree - Top 5% - pool, spa","annual_rev":51300,"adr":289,"occ":0.43,"rating":5.0,"reviews":290,"airbnb_link":"https://www.airbnb.com/rooms/594431834252436458","notes":"Pool, Spa"},
    {"address":"2088 Acoma Trail, Landers, CA 92285","listing_name":"The Yucca Escape","annual_rev":57500,"adr":170,"occ":0.732,"rating":4.9,"reviews":156,"airbnb_link":"https://www.airbnb.com/rooms/49210867","notes":"Pool, Hot Tub, Record Player, Hammock, Fire Pit"},
    {"address":"GPS: 34.30735, -116.44860 (unlisted)","listing_name":"Peaceful 2 Bedroom High Desert Getaway on 5 acres!","annual_rev":34200,"adr":216,"occ":0.356,"rating":5.0,"reviews":127,"airbnb_link":"https://www.airbnb.com/rooms/558173728228318872","notes":""},
    {"address":"3275 Dusty Mile Rd, Landers, CA 92285","listing_name":"Serene Retreat: Spa, Stars, Fire pit, Pet-friendly","annual_rev":39300,"adr":228,"occ":0.375,"rating":4.9,"reviews":179,"airbnb_link":"https://www.airbnb.com/rooms/644497332324732000","notes":""},
    {"address":"55150 Gleason Rd, Landers, CA 92285","listing_name":"Modern Desert Cabin-Hot Tub/Fire Pit/BBQ","annual_rev":37200,"adr":168,"occ":0.493,"rating":5.0,"reviews":221,"airbnb_link":"https://www.airbnb.com/rooms/653756316774444736","notes":""},
    {"address":"55960 Einstein Rd, Landers, CA 92285","listing_name":"Star Gazing | Outdoor Shower | Cowboy Pool | Spa","annual_rev":41000,"adr":208,"occ":0.441,"rating":5.0,"reviews":167,"airbnb_link":"https://www.airbnb.com/rooms/813255678900589319","notes":""},
]

# ===== TOP 5 COMPUTATION =====
top5_pool = {}
def collect(props, source_label):
    for p in props:
        f = p.get("fin", {})
        coc = f.get("coc")
        if coc is None: continue
        key = p["address"].split(",")[0]
        existing = top5_pool.get(key)
        if not existing or existing["fin"]["coc"] < coc:
            top5_pool[key] = dict(p, _source=source_label)

collect(laquinta_tab, "🌴 La Quinta")
collect(bigbear_tab, "🏔️ Big Bear")
collect(adu_tab, "🏠 ADU")
collect(money_tab, "🌵 Desert")
# sold_tab intentionally excluded from Top 5

top5_tab = sorted(top5_pool.values(), key=lambda p: p["fin"]["coc"], reverse=True)[:5]

# ===== CSS =====
css = '''
* { box-sizing: border-box; margin: 0; padding: 0; }
:root { --bg:#E8E4DB;--surface:#F7F4EC;--surface2:#DDD7C9;--border:#D3CCBC;--text:#26261F;--text2:#6E6A5E;--accent:#f97316;--green:#15803d;--red:#dc2626; }
body { background:var(--bg);color:var(--text);font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;min-height:100vh; }
.app-header { background:var(--bg);padding:18px 24px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:center;text-align:center;gap:14px; }
.app-header .title-row { display:flex;align-items:center;justify-content:center;gap:12px; }
.app-header .title-row img { height:56px;width:56px;object-fit:contain; }
.app-header h1 { font-family:'Anton',sans-serif;font-size:3.4rem;line-height:1;font-weight:400;text-transform:uppercase;letter-spacing:0.5px; }
.app-header .sub { font-size:0.8rem;color:var(--text2);margin-top:2px; }
.tabs-bar { background:var(--surface);border-bottom:1px solid var(--border);padding:0 12px;display:flex;justify-content:safe center;overflow-x:auto;gap:0; }
.tabs-bar::-webkit-scrollbar { height:3px; }
.tabs-bar::-webkit-scrollbar-thumb { background:var(--border); }
.tab-btn { background:transparent;border:none;color:var(--text2);padding:13px 16px;font-size:0.82rem;cursor:pointer;border-bottom:3px solid transparent;white-space:nowrap;transition:all 0.15s;font-weight:500; }
.tab-btn:hover { color:var(--text); }
.tab-btn.active { color:var(--accent);border-bottom-color:var(--accent);font-weight:600; }
.tab-btn.top5-btn { color:#B45309; }
.tab-btn.top5-btn.active { color:#B45309;border-bottom-color:#B45309; }
.tab-btn.sold-btn { color:#B91C1C; }
.tab-btn.sold-btn.active { color:#B91C1C;border-bottom-color:#B91C1C; }
.tab-content { padding:20px 16px 48px;max-width:1400px;margin:0 auto; }
.tab-header { display:flex;align-items:baseline;gap:10px;margin-bottom:18px; }
.tab-header h2 { font-family:'Anton',sans-serif;font-size:1.2rem;font-weight:400;text-transform:uppercase;letter-spacing:0.4px; }
.prop-count { font-size:0.72rem;color:var(--text2);background:var(--surface2);padding:2px 8px;border-radius:99px; }
.cards-grid { display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:18px; }
#tab-top5 .cards-grid { grid-template-columns:repeat(5,1fr);gap:14px; }
@media (max-width:1200px) { #tab-top5 .cards-grid { grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:18px; } }
.property-card { background:var(--surface);border-radius:12px;overflow:hidden;border:1px solid var(--border);transition:transform 0.2s,box-shadow 0.2s;display:flex;flex-direction:column; }
.property-card:hover { transform:translateY(-3px);box-shadow:0 10px 30px rgba(0,0,0,0.12); }
.property-card.card-green { border-color:rgba(34,197,94,0.45);background:linear-gradient(180deg,rgba(34,197,94,0.10) 0%,var(--surface) 28%); }
.property-card.card-green:hover { box-shadow:0 10px 30px rgba(34,197,94,0.18); }
.property-card.card-red { border-color:rgba(239,68,68,0.45);background:linear-gradient(180deg,rgba(239,68,68,0.10) 0%,var(--surface) 28%); }
.property-card.card-red:hover { box-shadow:0 10px 30px rgba(239,68,68,0.18); }
.card-image { position:relative;height:175px;overflow:hidden;background:linear-gradient(135deg,#d8d2c4 0%,#ccd6ca 50%,#d6cfdd 100%);flex-shrink:0; }
.card-image img { width:100%;height:100%;object-fit:cover;display:block;transition:transform 0.3s; }
.property-card:hover .card-image img { transform:scale(1.03); }
.card-image.img-fallback { display:flex;align-items:center;justify-content:center;font-size:2.5rem; }
.price-badge { position:absolute;bottom:10px;left:10px;background:rgba(0,0,0,0.75);color:#fff;padding:4px 11px;border-radius:6px;font-size:0.88rem;font-weight:700;backdrop-filter:blur(6px);letter-spacing:-0.3px; }
.card-body { padding:13px 14px 14px;display:flex;flex-direction:column;gap:10px;flex:1; }
.card-address { font-size:0.88rem;font-weight:600;line-height:1.3; }
.card-city { font-size:0.75rem;color:var(--text2);margin-top:-6px; }
.card-chips { display:grid;grid-template-columns:repeat(3,1fr);gap:6px; }
.chip { font-size:0.8rem;padding:6px 8px;border-radius:99px;font-weight:500;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.chip-bed { background:#DBE7F4;color:#1E5A96; }
.chip-bath { background:#D9EDF2;color:#0E7490; }
.chip-sqft { background:#E6E0F2;color:#6D28D9; }
.chip-region { background:#DCEAD9;color:#166534; }
.chip-source { background:#ECDFF2;color:#7E22CE; }
.chip-dom-green { background:#D9ECD9;color:#15803D;border:1px solid rgba(21,128,61,0.35); }
.chip-dom-yellow { background:#F3E8CD;color:#A16207;border:1px solid rgba(161,98,7,0.35); }
.chip-dom-red { background:#F4DCD7;color:#B91C1C;border:1px solid rgba(185,28,28,0.35); }
.price-badge del { color:#94a3b8;font-size:0.72rem;font-weight:400;letter-spacing:0;margin-right:3px;text-decoration:line-through; }
.fav-btn { position:absolute;top:10px;right:10px;width:34px;height:34px;border-radius:50%;border:none;background:rgba(0,0,0,0.55);color:#fff;font-size:1.05rem;line-height:1;cursor:pointer;backdrop-filter:blur(6px);display:flex;align-items:center;justify-content:center;padding:0;transition:transform 0.12s,color 0.15s; }
.fav-btn:hover { transform:scale(1.12); }
.fav-btn.active { color:#ef4444; }
.sold-overlay { position:absolute;top:10px;right:54px;background:#ef4444;color:#fff;padding:4px 10px;border-radius:6px;font-size:0.75rem;font-weight:800;letter-spacing:0.5px;text-transform:uppercase;box-shadow:0 2px 6px rgba(0,0,0,0.4); }
.property-card.card-sold { opacity:0.65;border-color:rgba(148,163,184,0.2); }
.property-card.card-sold:hover { transform:none;box-shadow:none; }
.cost-breakdown { background:rgba(0,0,0,0.05);border-radius:8px;padding:10px 11px; }
.cost-row { display:flex;justify-content:space-between;align-items:center;padding:3.5px 0;font-size:0.78rem; }
.total-row { border-top:1px solid var(--border);margin-top:5px;padding-top:6px;font-weight:700;font-size:0.82rem; }
.cost-row .label { color:var(--text2); }
.amount { font-weight:600;font-family:ui-monospace,'SF Mono',monospace;letter-spacing:-0.3px; }
.amount.neutral { color:#1D4ED8; }
.amount.positive { color:var(--green); }
.amount.negative { color:var(--red); }
.no-data-msg { font-size:0.75rem;color:var(--text2);text-align:center;padding:8px; }
.coc-section { display:flex;align-items:center;gap:8px; }
.coc-label { font-size:0.7rem;color:var(--text2);white-space:nowrap; }
.coc-bar-wrap { flex:1;height:5px;background:var(--surface2);border-radius:3px;overflow:hidden; }
.coc-bar { height:100%;border-radius:3px; }
.coc-value { font-size:0.8rem;font-weight:700;font-family:ui-monospace,'SF Mono',monospace;min-width:50px;text-align:right;white-space:nowrap; }
.coc-positive { color:var(--green); }
.coc-negative { color:var(--red); }
.coc-na { color:var(--text2); }
.rev-adjust { background:rgba(96,165,250,0.07);border:1px solid rgba(96,165,250,0.2);border-radius:8px;padding:9px 11px; }
.rev-adjust-header { display:flex;align-items:center;justify-content:space-between;margin-bottom:7px; }
.rev-adjust-title { font-size:0.7rem;font-weight:700;color:#1D4ED8; }
.rev-tag { font-size:0.65rem;background:rgba(96,165,250,0.15);color:#1D4ED8;padding:2px 6px;border-radius:99px;font-style:italic; }
.rev-adjust-row { display:flex;justify-content:space-between;align-items:center;font-size:0.75rem;color:var(--text2); }
.rev-input { background:#FFFDF7;border:1px solid var(--border);border-radius:5px;color:var(--text);font-size:0.78rem;font-family:ui-monospace,'SF Mono',monospace;padding:3px 7px;width:100px;text-align:right;transition:border-color 0.15s; }
.rev-input:focus { outline:none;border-color:#60a5fa; }
.startup-section { background:rgba(249,115,22,0.08);border:1px solid rgba(249,115,22,0.2);border-radius:8px;padding:10px 11px; }
.startup-title { font-size:0.7rem;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:0.6px;margin-bottom:7px; }
.startup-row { display:flex;justify-content:space-between;align-items:center;font-size:0.75rem;padding:2.5px 0;color:var(--text2); }
.startup-row span:last-child { font-weight:600;color:var(--text);font-family:ui-monospace,'SF Mono',monospace; }
.startup-total { border-top:1px solid rgba(249,115,22,0.25);margin-top:5px;padding-top:6px;font-weight:700; }
.startup-total span { color:var(--accent) !important;font-size:0.82rem !important; }
.remodel-input { background:#FFFDF7;border:1px solid var(--border);border-radius:5px;color:var(--text);font-size:0.78rem;font-family:ui-monospace,'SF Mono',monospace;padding:3px 7px;width:100px;text-align:right;transition:border-color 0.15s; }
.remodel-input:focus { outline:none;border-color:var(--accent); }
.card-links { display:flex;gap:8px;margin-top:auto; }
.comp-strips { display:flex;flex-direction:column;gap:6px;margin-top:8px; }
.comp-strips-title { font-size:0.68rem;font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:0.5px; }
.comp-strip { display:flex;align-items:center;justify-content:space-between;gap:6px;padding:7px 10px;border-radius:7px;background:#F3EEE3;border:1px solid var(--border);color:var(--text);font-size:0.74rem;font-weight:600;text-decoration:none;transition:background 0.15s,transform 0.1s; }
.comp-strip:hover { background:#EDE6D6;transform:translateY(-1px); }
.comp-strip .cs-arrow { color:var(--text2);font-weight:400; }
.listing-btn { flex:1;text-align:center;padding:7px 10px;border-radius:7px;font-size:0.76rem;font-weight:600;text-decoration:none;transition:opacity 0.15s,transform 0.1s; }
.listing-btn:hover { opacity:0.88;transform:translateY(-1px); }
.zillow-btn { background:#1a5f8a;color:#fff; }
.airbnb-btn { background:#7c1f3a;color:#fff; }
.comp-grid { display:grid;grid-template-columns:repeat(auto-fill,minmax(275px,1fr));gap:15px; }
.comp-card { background:var(--surface);border-radius:10px;padding:14px;border:1px solid var(--border);transition:transform 0.15s; }
.comp-card:hover { transform:translateY(-2px); }
.comp-address { font-size:0.83rem;font-weight:600; }
.comp-city { font-size:0.73rem;color:var(--text2);margin-top:2px; }
.comp-listing-name { font-size:0.72rem;color:var(--accent);margin-top:4px;margin-bottom:8px;font-style:italic;line-height:1.3; }
.comp-metrics { display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px; }
.comp-metric { background:rgba(0,0,0,0.05);padding:6px 8px;border-radius:6px; }
.cm-label { display:block;font-size:0.65rem;color:var(--text2);margin-bottom:2px;text-transform:uppercase;letter-spacing:0.3px; }
.cm-value { font-size:0.82rem;font-weight:600; }
.cm-value.green { color:var(--green); }
.occ-bar-wrap { height:4px;background:var(--surface2);border-radius:3px;overflow:hidden;margin-bottom:8px; }
.occ-bar { height:100%;border-radius:3px; }
.comp-notes { font-size:0.7rem;color:var(--text2);background:rgba(0,0,0,0.05);border-radius:5px;padding:5px 7px;margin-bottom:8px;line-height:1.4; }
.comp-header { margin-bottom:4px; }
#fav-map { height:400px;border-radius:12px;border:1px solid var(--border);margin-top:20px;z-index:0; }
.top5-banner { background:linear-gradient(135deg,rgba(245,158,11,0.12) 0%,rgba(249,115,22,0.08) 100%);border:1px solid rgba(245,158,11,0.25);border-radius:10px;padding:12px 16px;margin-bottom:20px;font-size:0.82rem;color:#92400E;line-height:1.5; }
'''

js = '''
function recalcCard(el) {
  var card = el.closest('.property-card');
  if (!card) return;
  var annualRev = parseFloat(card.dataset.annualRev) || 0;
  var piti = parseFloat(card.dataset.piti) || 0;
  var pool = parseFloat(card.dataset.pool) || 0;
  var baseStartup = parseFloat(card.dataset.baseStartup) || 0;
  var remodelEl = card.querySelector('.remodel-input');
  var remodel = remodelEl ? (parseFloat((remodelEl.value||'0').replace(/[^0-9.]/g,''))||0) : 0;
  var revEl = card.querySelector('.rev-input');
  var adjRev = revEl ? (parseFloat((revEl.value||String(annualRev)).replace(/[^0-9.]/g,''))||annualRev) : annualRev;
  var startup = baseStartup + remodel;
  var mo = adjRev / 12;
  var cleaning = mo * 0.23;
  var cf = mo - piti - cleaning - pool;
  var coc = startup > 0 ? (cf * 12 / startup * 100) : 0;
  var moRevEl = card.querySelector('.mo-rev-val');
  if (moRevEl) moRevEl.textContent = '+$' + Math.round(mo).toLocaleString() + '/mo';
  var cleanEl = card.querySelector('.cleaning-val');
  if (cleanEl) cleanEl.textContent = '-$' + Math.round(cleaning).toLocaleString() + '/mo';
  var cfEl = card.querySelector('.net-cf-val');
  if (cfEl) { cfEl.textContent=(cf>=0?'+':'-')+'$'+Math.round(Math.abs(cf)).toLocaleString()+'/mo'; cfEl.className='amount net-cf-val '+(cf>=0?'positive':'negative'); }
  var stEl = card.querySelector('.startup-total-val');
  if (stEl) stEl.textContent = '$' + Math.round(startup).toLocaleString();
  var cocValEl = card.querySelector('.coc-value');
  if (cocValEl) { cocValEl.textContent=(coc>=0?'+':'')+coc.toFixed(1)+'%'; cocValEl.className='coc-value '+(coc>=0?'coc-positive':'coc-negative'); }
  var cocBar = card.querySelector('.coc-bar');
  if (cocBar) { var c=Math.min(Math.max(coc,-20),50); var w=Math.max(0,Math.min(100,(c+20)/70*100)); cocBar.style.width=w.toFixed(1)+'%'; cocBar.style.background=coc>=0?'#22c55e':'#ef4444'; }
  card.classList.remove('card-green','card-red');
  if (coc>0) card.classList.add('card-green'); else if (coc<0) card.classList.add('card-red');
}
function showTab(id) {
  document.querySelectorAll('.tab-content').forEach(el=>el.style.display='none');
  document.querySelectorAll('.tab-btn').forEach(el=>el.classList.remove('active'));
  var el=document.getElementById('tab-'+id); if(el) el.style.display='block';
  var btn=document.getElementById('btn-'+id); if(btn) btn.classList.add('active');
  if(id==='only') setTimeout(function(){ if(favMap) favMap.invalidateSize(); updateFavMap(); },60);
}
var FAV_KEY='strFavs';
var favDefaults=__FAV_DEFAULTS__;
var favs;
try { favs=JSON.parse(localStorage.getItem(FAV_KEY)); } catch(e) { favs=null; }
if (!Array.isArray(favs)) favs=favDefaults.slice();
function saveFavs(){ try{ localStorage.setItem(FAV_KEY, JSON.stringify(favs)); }catch(e){} }
function toggleFav(btn){
  var card=btn.closest('.property-card'); if(!card) return;
  var addr=card.dataset.addr;
  var i=favs.indexOf(addr);
  if(i>=0) favs.splice(i,1); else favs.push(addr);
  saveFavs(); refreshFavs();
}
var favMap=null, favMarkers=[];
function updateFavMap(){
  var mapEl=document.getElementById('fav-map');
  if(!mapEl||typeof L==='undefined') return;
  if(!favMap){
    favMap=L.map('fav-map',{scrollWheelZoom:false});
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'&copy; OpenStreetMap contributors'}).addTo(favMap);
  }
  favMarkers.forEach(function(m){favMap.removeLayer(m);});
  favMarkers=[]; var pts=[];
  var grid=document.querySelector('#tab-only .cards-grid'); if(!grid) return;
  grid.querySelectorAll('.property-card').forEach(function(c){
    if(c.style.display==='none') return;
    var lat=parseFloat(c.dataset.lat), lng=parseFloat(c.dataset.lng);
    if(isNaN(lat)||isNaN(lng)) return;
    var badge=c.querySelector('.price-badge');
    var html='<b>'+(c.dataset.addr||'').split(',')[0]+'</b>'+(badge?'<br>'+badge.textContent:'');
    var m=L.marker([lat,lng]).addTo(favMap).bindPopup(html);
    favMarkers.push(m); pts.push([lat,lng]);
  });
  if(pts.length) favMap.fitBounds(pts,{padding:[30,30],maxZoom:13});
}
function refreshFavs(){
  var grid=document.querySelector('#tab-only .cards-grid'); if(!grid) return;
  grid.querySelectorAll('.fav-clone').forEach(function(el){el.remove();});
  var cloned={};
  document.querySelectorAll('.tab-content:not(#tab-only):not(#tab-top5) .property-card').forEach(function(c){
    var addr=c.dataset.addr;
    if(favs.indexOf(addr)>=0){
      c.style.display='none';
      if(!cloned[addr]){
        var clone=c.cloneNode(true);
        clone.classList.add('fav-clone');
        clone.style.display='';
        grid.appendChild(clone);
        cloned[addr]=true;
      }
    } else {
      c.style.display='';
    }
  });
  document.querySelectorAll('.property-card').forEach(function(c){
    var b=c.querySelector('.fav-btn');
    if(b) b.classList.toggle('active', favs.indexOf(c.dataset.addr)>=0);
  });
  document.querySelectorAll('.tab-content').forEach(function(t){
    var cnt=t.querySelector('.prop-count');
    if(!cnt||!t.querySelector('.cards-grid')) return;
    var n=0; t.querySelectorAll('.cards-grid .property-card').forEach(function(c){ if(c.style.display!=='none') n++; });
    cnt.textContent=n+' properties';
  });
  updateFavMap();
}
refreshFavs();
showTab('top5');
'''

tabs_def = [
    ("top5",    "🏆 Top 5",       top5_tab,       False, True),
    ("only",    "❤️ Favorites",   [],       False, False),
    ("money",   "🌵 Desert",      money_tab,      False, False),
    ("bigbear", "🏔️ Big Bear",   bigbear_tab,    False, False),
    ("adu",     "🏠 ADU",         adu_tab,        False, False),
    ("laquinta","🌴 La Quinta",   laquinta_tab,   False, False),
    ("sold",    "🔴 Sold",        sold_tab,       False, False),
    ("comps",   "📍 Mesquite Competition",comp_tracker,   True,  False),
]

def render_tab(tid, title, props, is_comp, show_sources):
    if is_comp:
        cards_html = "\n    ".join(comp_card(p) for p in props)
        grid_class = "comp-grid"
    else:
        if show_sources:
            cards_html = "\n    ".join(card(p, show_source=p.get('_source')) for p in props)
        else:
            cards_html = "\n    ".join(card(p) for p in props)
        grid_class = "cards-grid"
    extra = ''
    suffix = '\n    <div id="fav-map"></div>' if tid == 'only' else ''
    if tid == 'top5':
        extra = '<div class="top5-banner">⚡ Best CoC across all tabs — deduplicated, highest-revenue version of each property shown. Adjust revenue or remodel budget on any card to see live CoC updates.</div>\n    '
    return f'''  <div id="tab-{tid}" class="tab-content" style="display:none">
    <div class="tab-header">
      <h2>{title}</h2>
      <span class="prop-count">{len(props)} properties</span>
    </div>
    {extra}<div class="{grid_class}">
    {cards_html}
    </div>{suffix}
  </div>'''

tabs_html = "\n".join(render_tab(tid,title,props,is_c,ss) for tid,title,props,is_c,ss in tabs_def)

btns_html = "\n    ".join(
    f'<button class="tab-btn{"  top5-btn" if tid=="top5" else "  sold-btn" if tid=="sold" else ""}{"  active" if i==0 else ""}" onclick="showTab(\'{tid}\')" id="btn-{tid}">{title}</button>'
    for i,(tid,title,props,is_c,ss) in enumerate(tabs_def)
)

import json as _json
js = js.replace("__FAV_DEFAULTS__", _json.dumps(FAV_DEFAULT_ADDRS))

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Inter:wght@400..700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<title>STR Deal Analyzer</title>
<link rel="icon" type="image/png" href="favicon.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<style>{css}</style>
</head>
<body>
<div class="app-header">
  <div>
    <div class="title-row"><img src="icon.png" alt=""><h1>STR Deal Analyzer</h1></div>
    <div class="sub">30% Down · 7.5% Rate · CoC = Total Cash In (DP + furnishing + agent + closing + remodel)</div>
  </div>
</div>
<div class="tabs-bar">
    {btns_html}
</div>
{tabs_html}
<script>{js}</script>
</body>
</html>'''

import os
HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, 'index.html'), 'w') as fh:
    fh.write(html)

sz = len(html)
print(f"Generated: {sz:,} bytes ({sz/1024:.0f} KB)")

print("\nTop 5:")
for p in top5_tab:
    print(f"  {p['address'].split(',')[0]:35s}  CoC:{p['fin']['coc']:+.1f}%  from:{p.get('_source')}")

# Auto-push to GitHub
try:
    token = open(os.path.join(os.path.dirname(HERE), '.github_token')).read().strip()
    repo = HERE
    import subprocess as sp
    sp.run(['git','-C',repo,'config','user.email','alexcomery@gmail.com'],check=True,capture_output=True)
    sp.run(['git','-C',repo,'config','user.name','Alex Comery'],check=True,capture_output=True)
    sp.run(['git','-C',repo,'remote','set-url','origin',f'https://YukonCamino:{token}@github.com/YukonCamino/str-analyzer.git'],check=True,capture_output=True)
    sp.run(['git','-C',repo,'add','index.html','gen_html3.py'],check=True,capture_output=True)
    r = sp.run(['git','-C',repo,'commit','-m',f'Update STR Analyzer - {datetime.date.today()}'],capture_output=True,text=True)
    if 'nothing to commit' in r.stdout+r.stderr:
        print("No changes to push.")
    else:
        sp.run(['git','-C',repo,'push'],check=True,capture_output=True)
        print("Pushed to GitHub successfully!")
except Exception as e:
    print(f"Push skipped: {e}")

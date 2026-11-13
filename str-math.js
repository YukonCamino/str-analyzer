/* str-math.js -- the short-term-rental deal maths, in one file.

   One function does the work:

     analyze({ price, beds, baths, sqft, pool, hotTub, yearBuilt,
               annualRevenue, occupancy, avgStay })
       -> { lines, noi, piAnnual, cashFlow, coc, dscr, breakevenOcc, maxPrice, ... }

   No DOM, no browser or extension APIs, no dependencies: the same file runs in
   a Chrome extension, a web page (<script type="module">) and Node. It is an
   ES module.

   Settings live in settings.json beside this file. DEFAULT_SETTINGS below is a
   copy of that file so analyze() works with nothing loaded; a host that wants
   the file to be the authority reads it and passes it as the second argument:

     analyze(input, settings)        // settings: any subset, merged over the defaults

   Conventions
     - percentages are percent (7.5 means 7.5%), never fractions
     - occupancy is a fraction (0.46 means 46%)
     - money is annual unless the name says Monthly
     - every cost comes back as a labelled line, so a cash-flow figure can
       always be taken apart */

export const DEFAULT_SETTINGS = {
  cleaningPerStay: 120,
  cleaningPerExtraBedroom: 25,
  cleaningPoolAdd: 40,
  suppliesPerStay: 15,
  cleaningPctIfNoOccupancy: 23,

  utilitiesInternetPerYear: 4692,
  poolRunningPerMonth: 250,
  hotTubRunningPerMonth: 180,
  adminPerYear: 600,
  repairsPerYear: 2000,
  poolRepairsPerYear: 1000,

  taxPctIfUnknown: 1.25,
  insurancePctOfPrice: 0.56,

  airbnbOldFeePct: 3,
  airbnbNewFeePct: 15.5,
  airbnbFeeOverridePct: 0,
  airbnbFeeSwitchDate: '2026-09-15',
  managementPct: 0,

  downPct: 30,
  ratePct: 7.5,
  termYears: 30,
  closingPct: 2,
  buyerAgentPct: 2.5,
  supplementalTaxPct: 1.25,
  furnishingPerSqft: 16,
  furnishing: 25000,

  avgStayNights: 3,
  targetCashOnCashPct: 0
};

const n = (v, fallback = 0) => (typeof v === 'number' && isFinite(v) ? v : fallback);
const pct = (v, fallback = 0) => n(v, fallback) / 100;
const money = (v) => '$' + Math.round(Math.abs(n(v))).toLocaleString('en-US');

/* Standard amortised payment. A zero rate degrades to straight division
   rather than dividing by zero. */
export function monthlyPayment(principal, annualRatePct, termYears) {
  const months = Math.max(1, Math.round(n(termYears, 30) * 12));
  const r = pct(annualRatePct) / 12;
  if (principal <= 0) return 0;
  if (r === 0) return principal / months;
  return principal * r / (1 - Math.pow(1 + r, -months));
}

/* Effective Airbnb fee on a trailing-twelve-month revenue figure read on a
   given day.

   Revenue figures are the top line, before Airbnb's cut. Until hosts were
   moved to the single host-paid fee they kept 97% of it; after, 84.5%. A
   trailing year read shortly after the switch is mostly old-fee revenue, so
   charging the new rate on all of it invents cost that never happened, and
   charging the old rate ignores the months that have. This weights each by
   the days it covers.

   It assumes hosts raised prices to keep their payout (which leaves the
   guest's total unchanged), so post-switch days carry more revenue per day,
   by (1 - old) / (1 - new); and that revenue is spread evenly over the year. */
export function blendedAirbnbFee(asOf, { oldPct = 3, newPct = 15.5, switchDate = DEFAULT_SETTINGS.airbnbFeeSwitchDate } = {}) {
  const today = asOf instanceof Date ? asOf : new Date(asOf);
  const sw = new Date(switchDate + 'T00:00:00Z');
  const DAY = 86400000;
  const postDays = Math.max(0, Math.min(365, Math.floor((today - sw) / DAY)));
  const preDays = 365 - postDays;
  const o = oldPct / 100, w = newPct / 100;
  const uplift = w < 1 ? (1 - o) / (1 - w) : 1;
  const revPre = preDays, revPost = postDays * uplift;
  const total = revPre + revPost;
  const rate = total > 0 ? (revPre * o + revPost * w) / total : w;
  return { pct: rate * 100, preDays, postDays };
}

/* The deal.

   Required for a result: price and annualRevenue.
   Used when given:       beds, sqft, pool, hotTub, occupancy, avgStay.
   Accepted, not yet used: baths, yearBuilt (no cost depends on them).

   Optional extras, for a host that knows more than the basics:
     adr               nightly rate; estimates the number of stays when
                       occupancy is unknown
     cleaningFee       the fee the listing actually charges per stay; replaces
                       the per-bedroom estimate
     cleaningFeeSource a short label for where that fee came from, shown on
                       the cleaning line (default "given")
     annualPropertyTax the listing's own tax figure; replaces the percentage
     hoaAnnual         homeowners' association dues per year
     asOf              the date the revenue figure was read (default: now);
                       drives the blended Airbnb fee
     remodel           what you expect to spend on works; added to the cash in

   Cleaning: with an occupancy (or a nightly rate) it is priced per stay. With
   neither, the number of stays is unknown, so cleaning and supplies together
   are taken as cleaningPctIfNoOccupancy of revenue.

   Cash in: down payment + buyer's agent + closing + supplemental tax (all a
   share of price) + furnishing (furnishingPerSqft x sqft, or the flat
   `furnishing` figure when the size is unknown) + remodel. */
export function analyze(input = {}, settings = {}) {
  const s = { ...DEFAULT_SETTINGS, ...(settings || {}) };

  const price = n(input.price);
  const beds = n(input.beds);
  const sqft = n(input.sqft);
  const remodel = Math.max(0, n(input.remodel));
  const hasPool = !!input.pool;
  const hasHotTub = !!input.hotTub;
  const revenue = n(input.annualRevenue);
  const occupancy = typeof input.occupancy === 'number' && isFinite(input.occupancy) ? input.occupancy : null;
  const adr = n(input.adr, null);
  const avgStay = Math.max(0.5, n(input.avgStay, n(s.avgStayNights, 3)));
  const asOf = input.asOf != null ? input.asOf : new Date();

  /* --- Airbnb's fee --------------------------------------------------- */
  const override = n(s.airbnbFeeOverridePct);
  const blend = blendedAirbnbFee(asOf, {
    oldPct: n(s.airbnbOldFeePct, 3), newPct: n(s.airbnbNewFeePct, 15.5),
    switchDate: s.airbnbFeeSwitchDate || DEFAULT_SETTINGS.airbnbFeeSwitchDate
  });
  const feePct = override > 0 ? override : blend.pct;
  const feeNote = override > 0
    ? `${override}% of revenue (your flat rate)`
    : (blend.postDays >= 365 ? `${n(s.airbnbNewFeePct)}% of revenue`
      : blend.postDays <= 0 ? `${n(s.airbnbOldFeePct)}% of revenue`
      : `${feePct.toFixed(1)}% blended: ${blend.preDays}d at ${n(s.airbnbOldFeePct)}%, ${blend.postDays}d at ${n(s.airbnbNewFeePct)}%`);
  const revenueRate = feePct / 100 + pct(s.managementPct);    // share of revenue that leaves with it

  /* --- stays, which drive the turnover costs --------------------------- */
  let stays = null;
  if (occupancy != null) stays = 365 * occupancy / avgStay;
  else if (adr > 0 && revenue > 0) stays = (revenue / adr) / avgStay;

  /* A fee the listing actually charges beats the per-bedroom estimate: a
     modelled number should never override a measured one. */
  const estimatedClean = n(s.cleaningPerStay)
    + Math.max(0, beds - 1) * n(s.cleaningPerExtraBedroom)
    + (hasPool ? n(s.cleaningPoolAdd) : 0);
  const givenClean = n(input.cleaningFee, 0);
  const cleanPerStay = givenClean > 0 ? givenClean : estimatedClean;
  const perStayCost = cleanPerStay + n(s.suppliesPerStay);
  /* No way to count stays: cleaning becomes a share of revenue instead. */
  const cleanByShare = stays == null;
  const cleanShare = cleanByShare ? pct(s.cleaningPctIfNoOccupancy) : 0;
  const cleanSource = cleanByShare ? 'share of revenue'
    : givenClean > 0 ? (input.cleaningFeeSource || 'given') : 'estimated';

  /* --- carrying costs --------------------------------------------------- */
  const givenTax = n(input.annualPropertyTax, 0);
  const taxKnown = givenTax > 0;
  const propertyTax = taxKnown ? givenTax : price * pct(s.taxPctIfUnknown);
  const insurance = price * pct(s.insurancePctOfPrice);
  const hoa = n(input.hoaAnnual, 0);

  const lines = [
    ...(cleanByShare
      ? [{ key: 'cleaning', label: 'Cleaning', amount: revenue * cleanShare,
           note: `${n(s.cleaningPctIfNoOccupancy)}% of revenue (no occupancy figure)` }]
      : [{ key: 'cleaning', label: 'Cleaning', amount: stays * cleanPerStay,
           note: `${Math.round(stays)} stays x ${money(cleanPerStay)} (${cleanSource})` },
         { key: 'supplies', label: 'Supplies', amount: stays * n(s.suppliesPerStay),
           note: `${Math.round(stays)} stays x ${money(s.suppliesPerStay)}` }]),
    { key: 'utilities', label: 'Utilities + internet', amount: n(s.utilitiesInternetPerYear) },
    ...(hasPool ? [{ key: 'poolUtil', label: 'Pool running cost',
      amount: n(s.poolRunningPerMonth) * 12, note: `${money(s.poolRunningPerMonth)}/mo` }] : []),
    ...(hasHotTub ? [{ key: 'hotTub', label: 'Hot tub running cost',
      amount: n(s.hotTubRunningPerMonth) * 12, note: `${money(s.hotTubRunningPerMonth)}/mo` }] : []),
    { key: 'admin', label: 'Admin / software', amount: n(s.adminPerYear) },
    { key: 'repairs', label: 'Repairs + maintenance', amount: n(s.repairsPerYear) },
    ...(hasPool ? [{ key: 'poolRepairs', label: 'Pool repairs', amount: n(s.poolRepairsPerYear) }] : []),
    { key: 'tax', label: 'Property tax', amount: propertyTax,
      note: taxKnown ? 'from the listing' : `${s.taxPctIfUnknown}% of price (assumed)` },
    { key: 'insurance', label: 'Insurance', amount: insurance, note: `${s.insurancePctOfPrice}% of price` },
    ...(hoa > 0 ? [{ key: 'hoa', label: 'HOA', amount: hoa }] : []),
    { key: 'platform', label: 'Airbnb fee', amount: revenue * feePct / 100, note: feeNote },
    ...(n(s.managementPct) > 0 ? [{ key: 'management', label: 'Management',
      amount: revenue * pct(s.managementPct), note: `${s.managementPct}% of revenue` }] : [])
  ];

  const operatingCosts = lines.reduce((t, l) => t + n(l.amount), 0);
  const noi = revenue - operatingCosts;

  /* --- financing ---------------------------------------------------------- */
  const down = price * pct(s.downPct);
  const principal = price - down;
  const piMonthly = monthlyPayment(principal, s.ratePct, s.termYears);
  const piAnnual = piMonthly * 12;
  const closing = price * pct(s.closingPct);
  const buyerAgent = price * pct(s.buyerAgentPct);
  const supplementalTax = price * pct(s.supplementalTaxPct);
  const furnishing = sqft > 0 ? sqft * n(s.furnishingPerSqft) : n(s.furnishing);
  const cashInvested = down + buyerAgent + closing + supplementalTax + furnishing + remodel;

  const cashFlow = noi - piAnnual;
  const coc = cashInvested > 0 ? cashFlow / cashInvested : null;
  const dscr = piAnnual > 0 ? noi / piAnnual : null;

  /* --- breakeven occupancy ----------------------------------------------
     Revenue, cleaning, supplies, the Airbnb fee and management all move with
     occupancy; everything else is fixed. Solved directly rather than by
     iteration, which also says plainly when no occupancy can cover the costs. */
  const VARIABLE = ['cleaning', 'supplies', 'platform', 'management'];
  const fixedCosts = lines.filter(l => !VARIABLE.includes(l.key))
    .reduce((t, l) => t + n(l.amount), 0) + piAnnual;
  let breakevenOcc = null;
  if (occupancy && occupancy > 0) {
    const slope = (revenue / occupancy) * (1 - revenueRate) - (365 / avgStay) * perStayCost;
    breakevenOcc = slope > 0 ? fixedCosts / slope : null;
  }
  /* Above 100% is arithmetic without meaning: a house cannot be booked more
     than every night. Reported, but flagged. */
  const breakevenReachable = breakevenOcc != null && breakevenOcc <= 1;

  /* The same breakeven as a revenue figure, which needs no occupancy when
     cleaning is a share of revenue. */
  let breakevenRevenue = null;
  if (breakevenOcc != null && occupancy > 0) breakevenRevenue = revenue * breakevenOcc / occupancy;
  else if (cleanByShare && (1 - revenueRate - cleanShare) > 0) breakevenRevenue = fixedCosts / (1 - revenueRate - cleanShare);

  /* --- the most you can pay -----------------------------------------------
     Cash flow is a straight line in price:

       cashFlow(P) = R(1 - f) - S - A - k P

       R  revenue                       f  Airbnb fee + management, as a share
       S  per-stay costs for the year   A  every flat annual cost
       k  the share of price paid out each year: insurance, property tax when
          it is a percentage, and the mortgage payment on the financed part

     maxPrice is the P at which cash flow equals the target cash-on-cash
     return on the cash that P requires (see "Cash in" above).
     With the target at 0 it is the breakeven price. Repairs, pool costs and
     HOA are flat, so they sit in A, not k. A tax figure taken from the
     listing is treated as flat too, so that at P = price this agrees with the
     lines above. */
  const target = pct(s.targetCashOnCashPct);
  const mortgageConstant = monthlyPayment(1, s.ratePct, s.termYears) * 12;
  const k = pct(s.insurancePctOfPrice)
    + (taxKnown ? 0 : pct(s.taxPctIfUnknown))
    + (1 - pct(s.downPct)) * mortgageConstant;
  const A = lines.filter(l => !VARIABLE.includes(l.key) && l.key !== 'insurance' && !(l.key === 'tax' && !taxKnown))
    .reduce((t, l) => t + n(l.amount), 0);
  const S = stays == null ? 0 : stays * perStayCost;
  const numerator = revenue * (1 - revenueRate - cleanShare) - S - A - target * (furnishing + remodel);
  const denominator = k + target * (pct(s.downPct) + pct(s.closingPct) + pct(s.buyerAgentPct) + pct(s.supplementalTaxPct));
  const maxPrice = (revenue > 0 && numerator > 0 && denominator > 0) ? numerator / denominator : null;

  return {
    /* the contract */
    lines, noi, piAnnual, cashFlow, coc, dscr, breakevenOcc, maxPrice,

    /* the rest of the working, for anything that wants to show it */
    ok: price > 0 && revenue > 0,
    price, revenue, occupancy, adr, avgStay, stays,
    hasPool, hasHotTub,
    cleanPerStay, cleanSource,
    airbnbFeePct: feePct,
    operatingCosts,
    down, principal, closing, buyerAgent, supplementalTax, furnishing, remodel, cashInvested,
    breakevenRevenue,
    piMonthly,
    cashFlowMonthly: cashFlow / 12,
    taxMonthly: propertyTax / 12,
    insuranceMonthly: insurance / 12,
    pitiMonthly: piMonthly + propertyTax / 12 + insurance / 12,
    breakevenReachable,
    occupancyHeadroom: (breakevenReachable && occupancy != null) ? occupancy - breakevenOcc : null,
    targetCashOnCashPct: n(s.targetCashOnCashPct)
  };
}

-- ============================================================
--  InfoBhoomi test data seed
--  Land: 40 parcels (+ the 1 already done = 41)
--  Buildings: all 50 (5001-5050)
-- ============================================================

DO $$
DECLARE
  -- ── value pools ─────────────────────────────────────────
  land_names      text[] := ARRAY[
    'Kularatne Gardens','Nawala Road Plot','Peradeniya Estate','Nugegoda Lane',
    'Galle Face Terrace','Rajagiriya Block','Kandy Road Lot','Moratuwa Parcel',
    'Battaramulla Tract','Mount Lavinia Plot','Dehiwala Corner','Wattala Extent',
    'Malabe Subdivision','Piliyandala Lot','Panadura Parcel','Kelaniya Block',
    'Kaduwela Tract','Ja-Ela Estate','Negombo Allotment','Homagama Plot',
    'Matara Road Lot','Gampaha Parcel','Kurunegala Block','Chilaw Estate',
    'Puttalam Tract','Anuradhapura Lot','Polonnaruwa Plot','Trincomalee Parcel',
    'Ampara Block','Batticaloa Tract','Jaffna Estate','Vavuniya Lot',
    'Mannar Plot','Kilinochchi Parcel','Mullativu Block','Badulla Estate',
    'Ratnapura Lot','Kegalle Plot','Nuwara Eliya Parcel','Monaragala Block'
  ];
  land_use_types  text[] := ARRAY['RES','COM','AGR','IND','RES','MIX','RES','COM','AGR','RES'];
  land_use_subs   text[] := ARRAY['Single Family','Retail Shop','Paddy Field','Light Industrial','Apartment','Mixed Commercial','Single Family','Office','Tea Estate','Duplex'];
  sl_land_types   text[] := ARRAY['LAND','LAND','LAND','LAND','LAND','LAND','LAND','LAND','LAND','LAND'];
  zoning_cats     text[] := ARRAY['R1','R2','C1','C2','AG','R1','R2','I1','OS','SP'];
  soil_types      text[] := ARRAY['CLAY','SAND','LOAM','SILT','ROCK','LOAM','CLAY','SAND','FILL','PEAT'];
  local_auths     text[] := ARRAY[
    'Colombo Municipal Council','Gampaha Urban Council','Kandy Municipal Council',
    'Galle Municipal Council','Matara Municipal Council','Kurunegala Urban Council',
    'Ratnapura Urban Council','Badulla Municipal Council','Jaffna Municipal Council',
    'Trincomalee Urban Council'
  ];
  postal_addrs    text[] := ARRAY[
    '12/A Main Street Colombo 05','34 Temple Road Kandy','56/B Beach Road Galle',
    '78 High Level Road Nugegoda','90 Baseline Road Colombo 09','23 Station Road Gampaha',
    '45 Lake Road Kurunegala','67 Hill Street Nuwara Eliya','89 Beach Road Negombo',
    '11 Queen Street Jaffna'
  ];
  elevations      numeric[] := ARRAY[5.5,12.0,18.3,24.7,31.2,8.9,45.1,6.3,55.8,102.4,
                                     14.6,22.1,38.0,9.7,67.3,11.2,29.5,43.8,16.0,88.2,
                                     7.4,19.8,34.2,48.6,62.0,25.5,41.3,57.7,74.1,90.5,
                                     3.8,17.2,33.6,50.0,66.4,82.8,99.2,13.5,27.9,44.3];
  slopes          numeric[] := ARRAY[0.5,1.2,2.8,4.1,6.3,0.8,3.5,1.0,8.2,12.5,
                                     2.1,0.3,5.7,1.8,9.4,0.6,4.2,7.1,2.5,15.0,
                                     1.4,3.0,6.8,0.9,11.2,2.3,4.9,8.5,1.7,13.8,
                                     0.4,2.7,5.2,7.8,10.3,0.7,3.4,6.0,9.6,12.9];
  veg_covers      text[] := ARRAY[
    'Grass lawn with coconut trees','Paddy field','Sparse shrubs',
    'Dense jungle cover','Ornamental garden','Rubber plantation',
    'Tea bushes on slope','Bare laterite soil','Mixed scrub vegetation',
    'Irrigated paddy with bunds'
  ];
  water_vals      text[] := ARRAY['Municipal piped','NWSDB main','Borehole pump','Paddy irrigation','Municipal piped','Well water','NWSDB main','Rainwater tank','Municipal piped','NWSDB main'];
  elec_vals       text[] := ARRAY['CEB grid 230V','Solar panels','CEB grid 230V','No supply','CEB grid 230V','CEB grid 230V','Generator','CEB grid 230V','CEB grid 230V','Solar+CEB'];
  drain_vals      text[] := ARRAY['Municipal drain','Open channel','Soak pit','Natural runoff','Municipal drain','Culvert drain','Open channel','Municipal drain','Canal drain','No drain'];
  gully_vals      text[] := ARRAY['None','Cesspit','None','None','Septic tank','None','Cesspit','None','Septic tank','None'];
  garbage_vals    text[] := ARRAY['CMC collection','Local authority','Burn on site','No service','CMC collection','Local authority','Compost pit','Local authority','CMC collection','No service'];
  land_values     numeric[] := ARRAY[4500000,8200000,12500000,6750000,3200000,22000000,9800000,15000000,7300000,18500000,
                                     5600000,11200000,9000000,4100000,17500000,6300000,13800000,8500000,5200000,24000000,
                                     3700000,7900000,11500000,6100000,19000000,8800000,14500000,9500000,4800000,21000000,
                                     5100000,10500000,7600000,13000000,6500000,16000000,9200000,4400000,12800000,8100000];
  mkt_values      numeric[] := ARRAY[6000000,11000000,16800000,9000000,4300000,29500000,13200000,20100000,9800000,24750000,
                                     7500000,15000000,12100000,5500000,23500000,8500000,18500000,11400000,7000000,32000000,
                                     5000000,10600000,15400000,8200000,25500000,11800000,19500000,12700000,6400000,28200000,
                                     6800000,14100000,10200000,17500000,8700000,21500000,12400000,5900000,17200000,10900000];
  tax_statuses    text[] := ARRAY['paid','paid','pending','paid','overdue','paid','paid','pending','paid','paid'];
  reg_dates       text[] := ARRAY['2015-04-12','2018-07-23','2010-01-05','2020-11-30','2012-06-15',
                                  '2017-03-08','2019-09-20','2011-08-14','2022-02-01','2014-05-17',
                                  '2016-10-29','2021-12-03','2013-07-11','2023-01-25','2009-03-30',
                                  '2018-11-07','2020-04-18','2015-08-22','2017-06-05','2019-12-14',
                                  '2012-02-28','2014-09-16','2016-05-03','2021-07-30','2010-11-19',
                                  '2022-08-09','2013-04-24','2015-01-11','2018-06-28','2020-09-02',
                                  '2011-12-15','2017-02-20','2019-05-07','2023-08-31','2016-11-14',
                                  '2014-03-27','2021-01-08','2012-10-03','2020-07-22','2009-06-18'];

  -- ── building pools ──────────────────────────────────────
  bld_names       text[] := ARRAY[
    'Sunrise Villa','Ocean View Apartments','Green Gables','Lotus Tower Block A',
    'Mountain View Residency','Riverside Complex','Heritage Manor','Blue Horizon Flats',
    'Palm Court','Silver Springs','Golden Gate Building','Sunset Heights',
    'Lakeside Tower','Cedar Ridge Apts','Maple House','Coral Bay Residency',
    'Diamond Square','Emerald Court','Falcon Heights','Garden City Block B',
    'Harbour View','Island Court','Jasmine Towers','Kingfisher Residency',
    'Liberty Square','Monsoon Villa','Neptune Flats','Old Harbour Apts',
    'Pavilion Court','Quantum Block','Rainbow Heights','Sapphire Residency',
    'Teak House','Unity Towers','Vista Point','Willow Court',
    'Xavier Apts','Yellow Stone','Zenith Tower','Amber Courts',
    'Blossom Flats','Crown Heights','Daffodil House','Eagle Ridge',
    'Forest View','Grand Manor','Hilltop Apts','Imperial Court',
    'Jade Palace','Kestrel House'
  ];
  bld_structures  text[] := ARRAY['MASONRY','CONC_REINF','STEEL_FRM','TIMBER','MASONRY','CONC_REINF','MASONRY','STEEL_FRM','TIMBER','CONC_REINF'];
  bld_conditions  text[] := ARRAY['GOOD','EXCELLENT','FAIR','GOOD','POOR','GOOD','EXCELLENT','FAIR','GOOD','GOOD'];
  bld_roofs       text[] := ARRAY['FLAT','GABLE','HIP','FLAT','GABLE','HIP','FLAT','DOME','MANSARD','GABLE'];
  bld_walls       text[] := ARRAY['Brick','Concrete block','Stone','Timber frame','Brick','Reinforced concrete','Adobe','Steel panel','Concrete block','Brick'];
  bld_use_types   text[] := ARRAY['Residential','Commercial','Mixed Use','Residential','Public','Commercial','Residential','Industrial','Mixed Use','Residential'];
  bld_prop_types  text[] := ARRAY['Freehold','State Land','Leasehold','Freehold','State Land','Freehold','Leasehold','Freehold','State Land','Freehold'];
  bld_postal      text[] := ARRAY[
    '10 Canal Road Colombo 02','25 Main Street Negombo','38 Beach Road Galle',
    '52 Temple Lane Kandy','67 High Street Matara','14 Station Road Kurunegala',
    '29 Lake View Drive Nuwara Eliya','44 Coastal Road Trincomalee',
    '58 Fort Road Jaffna','73 Harbour Street Batticaloa',
    '11 Queen Street Colombo 01','26 Park Avenue Gampaha','39 Hill Road Badulla',
    '53 River Drive Ratnapura','68 Garden Lane Kegalle','15 Beach Strip Chilaw',
    '30 Market Road Vavuniya','45 East Street Ampara','59 West Lane Mannar',
    '74 Central Avenue Anuradhapura','12 Royal Gardens Colombo 07',
    '27 Lotus Road Moratuwa','40 Palm Grove Panadura','54 Sea View Kalutara',
    '69 Mountain Pass Hatton','16 Valley Road Nawalapitiya','31 Tea Estate Haputale',
    '46 Summit Drive Ella','60 Lake Shore Polonnaruwa','75 Ancient City Rd Sigiriya',
    '13 New Town Hambantota','28 Harbour View Mirissa','41 Surf Point Arugam Bay',
    '55 Fort Lane Trinco East','70 Stadium Road Dambulla','17 Spice Garden Matale',
    '32 Blue Waters Tangalle','47 Lagoon Drive Puttalam','61 Beach Front Dikwella',
    '76 Hill Country Bandarawela','14 Resort Drive Bentota','29 Jungle Edge Sinharaja',
    '42 Tea Trail Nuwara','56 Misty Heights Horton','71 Paddy View Polonnaruwa 2',
    '18 Bay Street Trinco 2','33 Colonial Row Galle Fort','48 Rock Face Sigiriya',
    '62 Sunrise Strip Arugam','77 End Of Road Dondra'
  ];
  bld_household   text[] := ARRAY['HH-001','HH-002','HH-003','HH-004','HH-005','HH-006','HH-007','HH-008','HH-009','HH-010'];
  bld_floors      int[]  := ARRAY[1,2,3,4,2,1,3,5,2,1,4,2,3,1,6,2,3,4,1,2,3,5,2,1,4,2,3,2,1,3,4,2,1,3,5,2,3,1,4,2,1,3,2,4,1,2,3,5,2,1];
  bld_years       int[]  := ARRAY[1985,1992,2001,2008,2015,1978,1995,2003,2010,2018,1988,1999,2005,2012,2020,1982,1997,2007,2013,2019,1990,2002,2009,2016,2022,1980,1993,2004,2011,2017,1986,1998,2006,2014,2021,1983,1996,2008,2015,2023,1987,2000,2004,2011,2018,1984,1994,2003,2012,2020];
  bld_heights     numeric[] := ARRAY[4.5,7.2,10.8,14.4,7.2,3.6,10.8,18.0,7.2,3.6,14.4,7.2,10.8,3.6,21.6,7.2,10.8,14.4,3.6,7.2,10.8,18.0,7.2,3.6,14.4,7.2,10.8,7.2,3.6,10.8,14.4,7.2,3.6,10.8,18.0,7.2,10.8,3.6,14.4,7.2,3.6,10.8,7.2,14.4,3.6,7.2,10.8,18.0,7.2,3.6];
  bld_mkt_vals    numeric[] := ARRAY[5500000,8200000,12500000,19800000,7300000,4100000,11000000,32500000,7800000,3900000,16200000,6800000,10500000,4500000,28000000,7200000,9800000,15500000,4800000,8500000,11200000,25000000,7500000,3700000,17800000,6500000,10200000,7700000,4200000,12800000,18500000,7100000,4000000,11500000,22000000,7600000,10900000,4600000,15000000,7400000,4300000,11800000,7300000,16500000,4100000,7200000,10600000,21000000,7600000,3800000];
  bld_tax_stats   text[] := ARRAY['paid','paid','pending','paid','overdue','paid','paid','pending','paid','paid'];
  bld_reg_dates   text[] := ARRAY['2001-06-15','1995-03-20','2008-11-07','2015-04-25','1982-09-12','2003-07-30','1998-02-14','2010-08-03','2017-12-22','1989-05-18','2004-10-09','1992-01-26','2007-06-14','2013-03-31','1985-11-05','2000-08-19','1996-04-07','2009-02-23','2016-09-11','1988-07-04','2002-12-16','1994-05-28','2006-03-13','2012-10-02','1983-06-30','2005-01-17','1999-08-25','2011-04-08','2018-07-19','1991-02-11','2003-09-27','1997-06-03','2008-12-20','2014-05-06','1986-10-22','2001-03-14','1995-12-29','2007-09-05','2015-06-18','1990-11-30','2004-04-21','1993-01-08','2006-08-15','2012-02-27','1984-07-13','2000-11-24','1996-06-10','2009-03-26','2017-10-08','1988-04-17'];

  -- ── loop vars ────────────────────────────────────────────
  rec         RECORD;
  i           int := 0;
  idx         int;
  max_far_v   numeric;
BEGIN

  -- ════════════════════════════════════════════════════════
  --  LAND PARCELS  — pick 40 su_ids without zoning yet
  -- ════════════════════════════════════════════════════════
  FOR rec IN
    SELECT sr.su_id
    FROM survey_rep sr
    WHERE sr.layer_id = 1
      AND sr.su_id NOT IN (SELECT su_id FROM la_ls_zoning)
      AND sr.su_id != 4542          -- already done
    ORDER BY sr.su_id DESC
    LIMIT 40
  LOOP
    i   := i + 1;
    idx := ((i - 1) % 10) + 1;   -- 1-based cycle of 10

    -- 1. la_ls_land_unit (always exists)
    UPDATE la_ls_land_unit SET
      land_name            = land_names[i] || ' ' || rec.su_id,
      access_road          = CASE WHEN i % 8 = 0 THEN 'No' ELSE 'Yes' END,
      postal_ad_lnd        = postal_addrs[idx],
      local_auth           = local_auths[idx],
      ext_landuse_type     = land_use_types[idx],
      ext_landuse_sub_type = land_use_subs[idx],
      sl_land_type         = 'LAND',
      registration_date    = reg_dates[i]::date
    WHERE su_id = rec.su_id;

    -- 2. la_ls_zoning (INSERT)
    max_far_v := CASE land_use_types[idx]
      WHEN 'AGR' THEN 0.5
      WHEN 'IND' THEN 3.0
      WHEN 'COM' THEN 4.0
      ELSE 2.0 + (i % 3) * 0.5
    END;
    INSERT INTO la_ls_zoning (su_id, zoning_category, max_building_height, max_coverage, max_far,
                               setback_front, setback_rear, setback_side, special_overlay)
    VALUES (
      rec.su_id,
      zoning_cats[idx],
      6 + (i % 7) * 2.5,
      40 + (i % 5) * 10,
      max_far_v,
      1.5 + (i % 4) * 0.5,
      1.0 + (i % 3) * 0.5,
      1.0 + (i % 2) * 0.5,
      CASE i % 5 WHEN 0 THEN 'Heritage Zone' WHEN 1 THEN 'Coastal Buffer' WHEN 2 THEN 'Forest Reserve' ELSE NULL END
    );

    -- 3. la_ls_physical_env (INSERT)
    INSERT INTO la_ls_physical_env (su_id, elevation, slope, soil_type, flood_zone, vegetation_cover)
    VALUES (
      rec.su_id,
      elevations[i],
      slopes[i],
      soil_types[idx],
      (i % 6 = 0),
      veg_covers[idx]
    );

    -- 4. la_ls_utinet_lu (always exists — UPDATE)
    UPDATE la_ls_utinet_lu SET
      water           = water_vals[idx],
      elec            = elec_vals[idx],
      drainage        = drain_vals[idx],
      sani_gully      = gully_vals[idx],
      garbage_dispose = garbage_vals[idx]
    WHERE su_id = rec.su_id;

    -- 5. assessment (always exists — UPDATE)
    UPDATE assessment SET
      land_value              = land_values[i],
      market_value            = mkt_values[i],
      assessment_annual_value = land_values[i],
      assessment_percentage   = 100.00,
      date_of_valuation       = (DATE '2020-01-01' + (i * 37) * INTERVAL '1 day')::date,
      year_of_assessment      = '2023',
      property_type           = CASE land_use_types[idx] WHEN 'RES' THEN 'Residential' WHEN 'COM' THEN 'Commercial' WHEN 'AGR' THEN 'Agricultural' ELSE 'Mixed' END,
      assessment_name         = land_names[i] || ' ' || rec.su_id,
      tax_status              = tax_statuses[idx]
    WHERE su_id = rec.su_id;

  END LOOP;

  -- ════════════════════════════════════════════════════════
  --  BUILDINGS  — all 50 (5001 – 5050)
  -- ════════════════════════════════════════════════════════
  i := 0;
  FOR rec IN
    SELECT sr.su_id
    FROM survey_rep sr
    WHERE sr.layer_id = 3
    ORDER BY sr.su_id
  LOOP
    i   := i + 1;
    idx := ((i - 1) % 10) + 1;

    -- 1. la_ls_build_unit (always exists — UPDATE)
    UPDATE la_ls_build_unit SET
      building_name       = bld_names[i],
      no_floors           = bld_floors[i],
      registration_date   = bld_reg_dates[i]::date,
      construction_year   = bld_years[i],
      structure_type      = bld_structures[idx],
      condition           = bld_conditions[idx],
      roof_type           = bld_roofs[idx],
      wall_type           = bld_walls[idx],
      access_road         = CASE WHEN i % 9 = 0 THEN 'No' ELSE 'Yes' END,
      postal_ad_build     = bld_postal[i],
      house_hold_no       = bld_household[idx],
      bld_property_type   = bld_prop_types[idx],
      ext_builduse_type   = bld_use_types[idx],
      hight               = bld_heights[i],
      surface_relation    = CASE i % 3 WHEN 0 THEN 'ON_GROUND' WHEN 1 THEN 'ABOVE_GROUND' ELSE 'ON_GROUND' END
    WHERE su_id = rec.su_id;

    -- 2. la_ls_utinet_bu (INSERT if not exists)
    INSERT INTO la_ls_utinet_bu (su_id, water, water_drink, elec, tele, internet,
                                  sani_sewer, sani_gully, garbage_dispose, drainage, status)
    SELECT
      rec.su_id,
      CASE idx WHEN 1 THEN 'Municipal' WHEN 2 THEN 'Borehole' WHEN 3 THEN 'Municipal' WHEN 4 THEN 'NWSDB' WHEN 5 THEN 'Municipal' WHEN 6 THEN 'Well' WHEN 7 THEN 'Municipal' WHEN 8 THEN 'Rainwater' WHEN 9 THEN 'Municipal' ELSE 'NWSDB' END,
      CASE idx WHEN 1 THEN 'Bottled' WHEN 2 THEN 'Filtered' WHEN 3 THEN 'Piped' WHEN 4 THEN 'Bottled' WHEN 5 THEN 'Filtered' WHEN 6 THEN 'Boiled' WHEN 7 THEN 'Piped' WHEN 8 THEN 'Bottled' WHEN 9 THEN 'Piped' ELSE 'Filtered' END,
      CASE idx WHEN 1 THEN 'CEB 230V' WHEN 2 THEN 'Solar' WHEN 3 THEN 'CEB 230V' WHEN 4 THEN 'Generator' WHEN 5 THEN 'CEB 230V' WHEN 6 THEN 'CEB 230V' WHEN 7 THEN 'Solar+CEB' WHEN 8 THEN 'CEB 230V' WHEN 9 THEN 'CEB 230V' ELSE 'CEB 230V' END,
      CASE idx WHEN 1 THEN 'SLT line' WHEN 2 THEN 'None' WHEN 3 THEN 'SLT line' WHEN 4 THEN 'Mobile' WHEN 5 THEN 'SLT line' WHEN 6 THEN 'None' WHEN 7 THEN 'SLT line' WHEN 8 THEN 'Mobile' WHEN 9 THEN 'SLT line' ELSE 'None' END,
      CASE idx WHEN 1 THEN 'Fibre' WHEN 2 THEN 'ADSL' WHEN 3 THEN 'Fibre' WHEN 4 THEN 'Mobile 4G' WHEN 5 THEN 'Fibre' WHEN 6 THEN 'None' WHEN 7 THEN 'ADSL' WHEN 8 THEN 'Mobile 4G' WHEN 9 THEN 'Fibre' ELSE 'ADSL' END,
      CASE idx WHEN 1 THEN 'Municipal sewer' WHEN 2 THEN 'Septic tank' WHEN 3 THEN 'Municipal sewer' WHEN 4 THEN 'Pit latrine' WHEN 5 THEN 'Municipal sewer' WHEN 6 THEN 'Septic tank' WHEN 7 THEN 'Municipal sewer' WHEN 8 THEN 'Septic tank' WHEN 9 THEN 'Municipal sewer' ELSE 'Septic tank' END,
      CASE idx WHEN 1 THEN 'None' WHEN 2 THEN 'Cesspit' WHEN 3 THEN 'None' WHEN 4 THEN 'Cesspit' WHEN 5 THEN 'None' WHEN 6 THEN 'Cesspit' WHEN 7 THEN 'None' WHEN 8 THEN 'Cesspit' WHEN 9 THEN 'None' ELSE 'Cesspit' END,
      CASE idx WHEN 1 THEN 'Council' WHEN 2 THEN 'Private' WHEN 3 THEN 'Council' WHEN 4 THEN 'Burn' WHEN 5 THEN 'Council' WHEN 6 THEN 'Compost' WHEN 7 THEN 'Council' WHEN 8 THEN 'Private' WHEN 9 THEN 'Council' ELSE 'Council' END,
      CASE idx WHEN 1 THEN 'Storm channel' WHEN 2 THEN 'Open drain' WHEN 3 THEN 'Underground' WHEN 4 THEN 'Natural' WHEN 5 THEN 'Storm channel' WHEN 6 THEN 'Open drain' WHEN 7 THEN 'Culvert' WHEN 8 THEN 'Natural' WHEN 9 THEN 'Storm channel' ELSE 'Open drain' END,
      true
    WHERE NOT EXISTS (SELECT 1 FROM la_ls_utinet_bu WHERE su_id = rec.su_id);

    -- 3. assessment (INSERT if not exists)
    INSERT INTO assessment (su_id, land_value, market_value, assessment_annual_value,
                             assessment_percentage, date_of_valuation, year_of_assessment,
                             property_type, assessment_name, tax_status, ass_out_balance)
    SELECT
      rec.su_id,
      0.00,
      bld_mkt_vals[i],
      bld_mkt_vals[i],
      100.00,
      (DATE '2020-06-01' + (i * 43) * INTERVAL '1 day')::date,
      '2023',
      bld_use_types[idx],
      bld_names[i],
      bld_tax_stats[idx],
      0.00
    WHERE NOT EXISTS (SELECT 1 FROM assessment WHERE su_id = rec.su_id);

  END LOOP;

  RAISE NOTICE 'Seed complete — land loop ran % iterations', i;
END $$;


import React from 'react';
import { SearchExpression } from './types';

export const SEARCH_EXPRESSIONS: SearchExpression[] = [
  {
    "id": "TERM_001",
    "title_en": "Nakba",
    "variants_en": ["Nakba", "Naqba", "ongoing Nakba"],
    "variants_he": ["נכבה", "נכבה מתמשכת"],
    "regex_en": "(?i)\\b(ongoing\\s+)?na[kq]ba\\b",
    "regex_he": "([ובהכשלו]|^)נכבה(\\s+מתמשכת)?"
  },
  {
    "id": "TERM_002",
    "title_en": "Colonialism",
    "variants_en": ["Colonialism", "settler-colonialism", "colonial"],
    "variants_he": ["קולוניאליזם", "קולוניאלי", "קולוניאליזם התישבותי"],
    "regex_en": "(?i)\\b(settler[- ])?colonial(ism|ist)?s?\\b",
    "regex_he": "([ובהכשלו]|^)קולוניאלי(זם|סט|י)?(\\s+התישבותי)?"
  },
  {
    "id": "TERM_003",
    "title_en": "Apartheid",
    "variants_en": ["Apartheid"],
    "variants_he": ["אפרטהייד"],
    "regex_en": "(?i)\\bapartheid\\b",
    "regex_he": "([ובהכשלו]|^)אפרטהייד"
  },
  {
    "id": "TERM_004",
    "title_en": "Jewish supremacy",
    "variants_en": ["Jewish supremacy"],
    "variants_he": ["עליונות יהודית"],
    "regex_en": "(?i)\\bJewish\\s+supremacy\\b",
    "regex_he": "([ובהכשלו]|^)עליונות\\s+יהודית"
  },
  {
    "id": "TERM_005",
    "title_en": "Zionism",
    "variants_en": ["Zionism", "Zionist", "Zionists"],
    "variants_he": ["ציונות", "ציוני", "ציוניים"],
    "regex_en": "(?i)\\bZionis(m|t)s?\\b",
    "regex_he": "([ובהכשלו]|^)ציונ(ות|י|ית|ים|יים)"
  },
  {
    "id": "TERM_006",
    "title_en": "Anti-Zionism",
    "variants_en": ["Anti-Zionism", "anti-Zionist"],
    "variants_he": ["אנטי-ציונות", "אנטי-ציוני"],
    "regex_en": "(?i)\\banti[- ]?Zionis(m|t)s?\\b",
    "regex_he": "([ובהכשלו]|^)אנטי[- ]?ציונ(ות|י|ית|ים|יים)"
  },
  {
    "id": "TERM_007",
    "title_en": "BDS / Boycott",
    "variants_en": ["BDS", "boycott"],
    "variants_he": ["חרם", "BDS"],
    "regex_en": "(?i)\\b(BDS|boycott(s|ing)?)\\b",
    "regex_he": "([ובהכשלו]|^)(חרם|BDS)"
  },
  {
    "id": "TERM_008",
    "title_en": "Coresistance",
    "variants_en": ["Coresistance", "co-resistance", "joint resistance"],
    "variants_he": ["התנגדות משותפת"],
    "regex_en": "(?i)\\b(co[- ]?resistance|joint\\s+resistance)\\b",
    "regex_he": "([ובהכשלו]|^)התנגדות\\s+משותפת"
  },
  {
    "id": "TERM_009",
    "title_en": "Joint struggle",
    "variants_en": ["Joint struggle"],
    "variants_he": ["מאבק משותף"],
    "regex_en": "(?i)\\bjoint\\s+struggle\\b",
    "regex_he": "([ובהכשלו]|^)מאבק\\s+משותף"
  },
  {
    "id": "TERM_010",
    "title_en": "Occupation",
    "variants_en": ["Occupation", "the occupation"],
    "variants_he": ["כיבוש"],
    "regex_en": "(?i)\\b(the\\s+)?occupation\\b",
    "regex_he": "([ובהכשלו]|^)כיבוש"
  },
  {
    "id": "TERM_011",
    "title_en": "Peace",
    "variants_en": ["Peace"],
    "variants_he": ["שלום"],
    "regex_en": "(?i)\\bpeace\\b",
    "regex_he": "([ובהכשלו]|^)שלום"
  },
  {
    "id": "TERM_012",
    "title_en": "Coexistence",
    "variants_en": ["Coexistence", "co-existence"],
    "variants_he": ["דו קיום", "דו-קיום"],
    "regex_en": "(?i)\\bco[- ]?existence\\b",
    "regex_he": "([ובהכשלו]|^)דו[- ]?קיום"
  },
  {
    "id": "TERM_013",
    "title_en": "Genocide",
    "variants_en": ["Genocide"],
    "variants_he": ["רצח עם", "ג׳נוסייד"],
    "regex_en": "(?i)\\bgenocide\\b",
    "regex_he": "([ובהכשלו]|^)(רצח\\s+עם|ג['׳]נוסייד)"
  },
  {
    "id": "TERM_014",
    "title_en": "Massacre",
    "variants_en": ["Massacre", "massacres"],
    "variants_he": ["טבח"],
    "regex_en": "(?i)\\bmassacre[sd]?\\b",
    "regex_he": "([ובהכשלו]|^)טבח"
  },
  {
    "id": "TERM_015",
    "title_en": "War Crimes",
    "variants_en": ["War crime", "war crimes", "war criminal", "war criminals"],
    "variants_he": ["פשע מלחמה", "פשעי מלחמה", "פושע מלחמה", "פושעי מלחמה"],
    "regex_en": "(?i)\\bwar\\s+crim(e|inal)s?\\b",
    "regex_he": "([ובהכשלו]|^)פשע(י)?\\s+מלחמה|([ובהכשלו]|^)פושע(י)?\\s+מלחמה"
  },
  {
    "id": "TERM_016",
    "title_en": "Crimes against humanity",
    "variants_en": ["Crime against humanity", "crimes against humanity"],
    "variants_he": ["פשע נגד האנושות", "פשעים נגד האנושות"],
    "regex_en": "(?i)\\bcrimes?\\s+against\\s+humanity\\b",
    "regex_he": "([ובהכשלו]|^)פשע(ים)?\\s+נגד\\s+האנושות"
  },
  {
    "id": "TERM_017",
    "title_en": "Fascism",
    "variants_en": ["Fascism", "Fascist", "Fascists"],
    "variants_he": ["פשיזם", "פשיסטים", "פשיסט"],
    "regex_en": "(?i)\\bfascis(m|t)s?\\b",
    "regex_he": "([ובהכשלו]|^)פשיז(ם|ט|טים)"
  },
  {
    "id": "TERM_018",
    "title_en": "Pogrom",
    "variants_en": ["Pogrom", "pogroms"],
    "variants_he": ["פוגרום"],
    "regex_en": "(?i)\\bpogroms?\\b",
    "regex_he": "([ובהכשלו]|^)פוגרום"
  },
  {
    "id": "TERM_019",
    "title_en": "Ethnic Cleansing",
    "variants_en": ["Ethnic cleansing"],
    "variants_he": ["טיהור אתני"],
    "regex_en": "(?i)\\bethnic\\s+cleansing\\b",
    "regex_he": "([ובהכשלו]|^)טיהור\\s+אתני"
  }
];

export const Icons = {
  Upload: () => (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
  ),
  Search: () => (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
  ),
  Chart: () => (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
  ),
  FileText: () => (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
  ),
  Download: () => (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
  )
};

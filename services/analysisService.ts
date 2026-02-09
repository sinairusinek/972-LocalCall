
import { SearchExpression, CorpusRow, AnalysisRowResult, TermMatch, SearchMode, AnalysisOptions, CorpusStats, ColumnStats, TimelineDataPoint, AnalysisCountMode, TimeAggregation } from '../types';

/**
 * JS RegExp doesn't support (?i) inline. We need to strip it and use 'i' flag.
 */
function compilePattern(pattern: string): RegExp | null {
  if (!pattern || pattern.trim() === '') return null;
  let p = pattern;
  let flags = 'g';
  if (p.startsWith('(?i)')) {
    p = p.substring(4);
    flags += 'i';
  }
  try {
    return new RegExp(p, flags);
  } catch (e) {
    console.error("Invalid regex:", p, e);
    return null;
  }
}

function countWords(text: string): number {
  if (!text) return 0;
  return text.trim().split(/\s+/).filter(Boolean).length;
}

export function calculateCorpusStats(data: CorpusRow[], selectedColumns: string[]): CorpusStats {
  const columnStats: Record<string, ColumnStats> = {};
  let totalWords = 0;

  selectedColumns.forEach(col => {
    columnStats[col] = { nonEmptyRows: 0, wordCount: 0 };
  });

  data.forEach(row => {
    selectedColumns.forEach(col => {
      const val = row[col] || '';
      if (val.trim()) {
        const words = countWords(val);
        columnStats[col].nonEmptyRows++;
        columnStats[col].wordCount += words;
        totalWords += words;
      }
    });
  });

  return {
    totalRows: data.length,
    totalWords,
    columnStats
  };
}

function parseDate(val: string): Date | undefined {
  if (!val) return undefined;
  const d = new Date(val);
  return isNaN(d.getTime()) ? undefined : d;
}

export async function analyzeCorpus(
  data: CorpusRow[],
  selectedColumns: string[],
  expressions: SearchExpression[],
  options: AnalysisOptions
): Promise<AnalysisRowResult[]> {
  const activeExpressions = expressions.filter(e => e.enabled !== false);
  
  const compiled = activeExpressions.map(exp => ({
    id: exp.id,
    title: exp.title_en,
    regEn: options.includeEnglish ? compilePattern(exp.regex_en) : null,
    regHe: options.includeHebrew ? compilePattern(exp.regex_he) : null,
  }));
  
  return data.map((row) => {
    const matches: TermMatch[] = [];
    let totalCount = 0;
    let rowWordCount = 0;

    const columnContents = selectedColumns.map(col => {
      const val = row[col] || '';
      rowWordCount += countWords(val);
      return val;
    });

    compiled.forEach((exp) => {
      let termCount = 0;
      const variantsFound = new Set<string>();

      const analyzeText = (text: string) => {
        if (exp.regEn) {
          const mEn = text.match(exp.regEn);
          if (mEn) {
            termCount += mEn.length;
            mEn.forEach(v => variantsFound.add(v.trim()));
          }
        }
        if (exp.regHe) {
          const mHe = text.match(exp.regHe);
          if (mHe) {
            termCount += mHe.length;
            mHe.forEach(v => variantsFound.add(v.trim()));
          }
        }
      };

      if (options.mode === SearchMode.CONCATENATED) {
        const fullText = columnContents.join(' ');
        analyzeText(fullText);
      } else {
        columnContents.forEach(text => analyzeText(text));
      }

      if (termCount > 0) {
        matches.push({
          termId: exp.id,
          termTitle: exp.title,
          count: termCount,
          variants: Array.from(variantsFound)
        });
        totalCount += termCount;
      }
    });

    const result: AnalysisRowResult = {
      originalRow: row,
      matches,
      totalMatches: totalCount,
      authors: [],
      wordCount: rowWordCount
    };

    if (options.dateColumn) {
      result.date = parseDate(row[options.dateColumn]);
    }

    if (options.authorColumn && row[options.authorColumn]) {
      result.authors = row[options.authorColumn]
        .split('|')
        .map(a => a.trim())
        .filter(Boolean);
    }

    return result;
  });
}

function getAggregatedKey(date: Date, aggregation: TimeAggregation): { key: string; label: string; start: number; end: number } {
  const d = new Date(date);
  if (aggregation === TimeAggregation.YEAR) {
    const start = new Date(d.getFullYear(), 0, 1).getTime();
    const end = new Date(d.getFullYear(), 11, 31, 23, 59, 59).getTime();
    return { key: d.getFullYear().toString(), label: d.getFullYear().toString(), start, end };
  }
  if (aggregation === TimeAggregation.MONTH) {
    const start = new Date(d.getFullYear(), d.getMonth(), 1).getTime();
    const end = new Date(d.getFullYear(), d.getMonth() + 1, 0, 23, 59, 59).getTime();
    const label = d.toLocaleDateString(undefined, { month: 'short', year: 'numeric' });
    return { key: `${d.getFullYear()}-${d.getMonth()}`, label, start, end };
  }
  // Default DAY
  const start = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const end = new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59).getTime();
  return { key: start.toString(), label: d.toLocaleDateString(), start, end };
}

export function prepareTimelineData(
  results: AnalysisRowResult[], 
  countMode: AnalysisCountMode = AnalysisCountMode.HITS,
  activeTerms: string[] = [],
  aggregation: TimeAggregation = TimeAggregation.DAY
): TimelineDataPoint[] {
  const dateMap: Record<string, TimelineDataPoint> = {};

  results.forEach(res => {
    if (!res.date) return;
    
    const { key, label, start, end } = getAggregatedKey(res.date, aggregation);

    if (!dateMap[key]) {
      dateMap[key] = {
        label,
        timestamp: start,
        counts: {},
        total: 0,
        dateRange: { start, end }
      };
    }

    res.matches.forEach(m => {
      if (activeTerms.length > 0 && !activeTerms.includes(m.termTitle)) return;

      const increment = countMode === AnalysisCountMode.ROWS ? 1 : m.count;
      dateMap[key].counts[m.termTitle] = (dateMap[key].counts[m.termTitle] || 0) + increment;
      dateMap[key].total += increment;
    });
  });

  return Object.values(dateMap).sort((a, b) => a.timestamp - b.timestamp);
}

export function prepareAuthorTimelineData(
  results: AnalysisRowResult[],
  activeAuthors: string[] = [],
  metric: 'POSTS' | 'WORDS' = 'POSTS',
  aggregation: TimeAggregation = TimeAggregation.DAY
): TimelineDataPoint[] {
  const dateMap: Record<string, TimelineDataPoint> = {};

  results.forEach(res => {
    if (!res.date) return;
    
    const { key, label, start, end } = getAggregatedKey(res.date, aggregation);

    if (!dateMap[key]) {
      dateMap[key] = { 
        label, 
        timestamp: start, 
        counts: {}, 
        total: 0, 
        dateRange: { start, end } 
      };
    }

    res.authors.forEach(author => {
      if (activeAuthors.length > 0 && !activeAuthors.includes(author)) return;
      const val = metric === 'POSTS' ? 1 : res.wordCount;
      dateMap[key].counts[author] = (dateMap[key].counts[author] || 0) + val;
      dateMap[key].total += val;
    });
  });

  return Object.values(dateMap).sort((a, b) => a.timestamp - b.timestamp);
}

export function parseTSV(text: string): CorpusRow[] {
  const lines = text.split(/\r?\n/).filter(line => line.trim() !== '');
  if (lines.length < 1) return [];

  const headers = lines[0].split('\t').map(h => h.trim());
  const rows: CorpusRow[] = [];

  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split('\t');
    const row: CorpusRow = {};
    headers.forEach((header, index) => {
      row[header] = values[index]?.trim() || '';
    });
    rows.push(row);
  }

  return rows;
}

export function generateResultsTSV(results: AnalysisRowResult[]): string {
  if (results.length === 0) return '';
  
  const headers = Object.keys(results[0].originalRow);
  const resultHeaders = ['Extracted Terms', 'Match Count', 'Total Count'];
  const fullHeaders = [...headers, ...resultHeaders];
  
  let tsv = fullHeaders.join('\t') + '\n';
  
  results.forEach(res => {
    const rowValues = headers.map(h => res.originalRow[h]);
    const termSummary = res.matches.map(m => `${m.termTitle} (${m.count})`).join(', ');
    const termCounts = res.matches.map(m => m.count).join(', ');
    
    const outputLine = [...rowValues, termSummary, termCounts, res.totalMatches.toString()];
    tsv += outputLine.join('\t') + '\n';
  });
  
  return tsv;
}

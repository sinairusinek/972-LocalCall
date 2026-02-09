
export interface SearchExpression {
  id: string;
  title_en: string;
  variants_en: string[];
  variants_he: string[];
  regex_en: string;
  regex_he: string;
  enabled?: boolean; // For selection in the list
}

export type CorpusRow = Record<string, string>;

export interface TermMatch {
  termId: string;
  termTitle: string;
  count: number;
  variants: string[];
}

export interface AnalysisRowResult {
  originalRow: CorpusRow;
  matches: TermMatch[];
  totalMatches: number;
  date?: Date;
  authors: string[];
  wordCount: number;
}

export interface ColumnStats {
  nonEmptyRows: number;
  wordCount: number;
}

export interface CorpusStats {
  totalRows: number;
  totalWords: number;
  columnStats: Record<string, ColumnStats>;
}

export enum SearchMode {
  CONCATENATED = 'CONCATENATED',
  SEPARATE = 'SEPARATE'
}

export enum AnalysisCountMode {
  HITS = 'HITS',
  ROWS = 'ROWS'
}

export enum TimeAggregation {
  DAY = 'DAY',
  MONTH = 'MONTH',
  YEAR = 'YEAR'
}

export interface AnalysisOptions {
  includeEnglish: boolean;
  includeHebrew: boolean;
  mode: SearchMode;
  countMode: AnalysisCountMode;
  dateColumn?: string;
  authorColumn?: string;
}

export interface TimelineDataPoint {
  label: string;
  timestamp: number;
  counts: Record<string, number>; // termTitle -> count
  total: number;
  dateRange: { start: number; end: number }; // For filtering by slice
}

export interface DashboardFilters {
  selectedTerms: string[];
  selectedAuthors: string[];
  keywordFilter: string;
  dateRange?: { start: number; end: number };
}

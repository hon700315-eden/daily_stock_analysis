import apiClient from './index';

export type ExtractItem = {
  code?: string | null;
  name?: string | null;
  confidence: string;
};

export type ExtractFromImageResponse = {
  codes: string[];
  items?: ExtractItem[];
  rawText?: string;
};

export type StockQuote = {
  stock_code: string;
  stock_name?: string | null;
  current_price: number;
  change?: number | null;
  change_percent?: number | null;
  open?: number | null;
  high?: number | null;
  low?: number | null;
  prev_close?: number | null;
  volume?: number | null;
  amount?: number | null;
  update_time?: string | null;
  market?: string | null;
  currency?: string | null;
  provider?: string | null;
  source?: string | null;
  symbol?: string | null;
  code?: string | null;
  exchange?: string | null;
  trade_date?: string | null;
  previous_close?: number | null;
  close?: number | null;
  pct_chg?: number | null;
  volume_shares?: number | null;
  volume_lots?: number | null;
  turnover_amount?: number | null;
  transaction_count?: number | null;
  data_status?: string | null;
  timezone?: string | null;
};

export type StockHistoryPoint = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number | null;
  amount?: number | null;
  change_percent?: number | null;
  transaction_count?: number | null;
  ma5?: number | null;
  ma10?: number | null;
  ma20?: number | null;
  ma60?: number | null;
  bollinger_upper?: number | null;
  bollinger_middle?: number | null;
  bollinger_lower?: number | null;
  kd_k?: number | null;
  kd_d?: number | null;
  macd_dif?: number | null;
  macd_signal?: number | null;
  macd_histogram?: number | null;
};

export type StockHistoryResponse = {
  stock_code: string;
  stock_name?: string | null;
  period: string;
  data: StockHistoryPoint[];
  source?: string | null;
  data_status?: string | null;
};

export type StockTechnicalResponse = {
  stock_code: string;
  stock_name?: string | null;
  trade_date?: string | null;
  source?: string | null;
  availability: string;
  indicators: Record<string, number | null | undefined>;
};

export const stocksApi = {
  async getQuote(stockCode: string): Promise<StockQuote> {
    const response = await apiClient.get<StockQuote>(
      `/api/v1/stocks/${encodeURIComponent(stockCode)}/quote`,
    );
    return response.data;
  },

  async getHistory(stockCode: string, days = 30): Promise<StockHistoryResponse> {
    const response = await apiClient.get<StockHistoryResponse>(
      `/api/v1/stocks/${encodeURIComponent(stockCode)}/history`,
      { params: { period: 'daily', days } },
    );
    return response.data;
  },

  async getTechnical(stockCode: string): Promise<StockTechnicalResponse> {
    const response = await apiClient.get<StockTechnicalResponse>(
      `/api/v1/stocks/${encodeURIComponent(stockCode)}/technical`,
    );
    return response.data;
  },

  async extractFromImage(file: File): Promise<ExtractFromImageResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const headers: { [key: string]: string | undefined } = { 'Content-Type': undefined };
    const response = await apiClient.post(
      '/api/v1/stocks/extract-from-image',
      formData,
      {
        headers,
        timeout: 60000, // Vision API can be slow; 60s
      },
    );

    const data = response.data as { codes?: string[]; items?: ExtractItem[]; raw_text?: string };
    return {
      codes: data.codes ?? [],
      items: data.items,
      rawText: data.raw_text,
    };
  },

  async parseImport(file?: File, text?: string): Promise<ExtractFromImageResponse> {
    if (file) {
      const formData = new FormData();
      formData.append('file', file);
      const headers: { [key: string]: string | undefined } = { 'Content-Type': undefined };
      const response = await apiClient.post('/api/v1/stocks/parse-import', formData, { headers });
      const data = response.data as { codes?: string[]; items?: ExtractItem[] };
      return { codes: data.codes ?? [], items: data.items };
    }
    if (text) {
      const response = await apiClient.post('/api/v1/stocks/parse-import', { text });
      const data = response.data as { codes?: string[]; items?: ExtractItem[] };
      return { codes: data.codes ?? [], items: data.items };
    }
    throw new Error('请提供文件或粘贴文本');
  },
};

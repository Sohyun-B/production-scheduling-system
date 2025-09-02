// API service configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8001/api/v1';

export interface Order {
  id: number;
  po_no: string;
  gitem: string;
  gitem_name?: string;
  width: number;
  length: number;
  request_amount: number;
  due_date: string;
  created_at: string;
  updated_at?: string;
}

export interface ScheduleRun {
  id: number;
  run_id: string;
  name: string;
  description?: string;
  status: string;
  makespan?: number;
  total_late_days?: number;
  total_orders?: number;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface ScheduleRequest {
  name: string;
  description?: string;
  input_file_path?: string;
}

export interface ProgressStep {
  id: number;
  run_id: string;
  step: string;
  step_name: string;
  status: string;
  progress_percent: number;
  current_item?: string;
  processed_count: number;
  total_count: number;
  started_at?: string;
  completed_at?: string;
  message?: string;
  error_message?: string;
  created_at: string;
}

class ApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Orders API
  async getOrders(): Promise<Order[]> {
    return this.request<Order[]>('/orders');
  }

  async createOrder(order: Omit<Order, 'id' | 'created_at' | 'updated_at'>): Promise<Order> {
    return this.request<Order>('/orders', {
      method: 'POST',
      body: JSON.stringify(order),
    });
  }

  async updateOrder(id: number, order: Partial<Order>): Promise<Order> {
    return this.request<Order>(`/orders/${id}`, {
      method: 'PUT',
      body: JSON.stringify(order),
    });
  }

  async deleteOrder(id: number): Promise<void> {
    await this.request(`/orders/${id}`, {
      method: 'DELETE',
    });
  }

  // Scheduling API
  async getScheduleRuns(): Promise<ScheduleRun[]> {
    return this.request<ScheduleRun[]>('/scheduling/runs');
  }

  async createScheduleRun(request: ScheduleRequest): Promise<ScheduleRun> {
    return this.request<ScheduleRun>('/scheduling/run', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getScheduleRun(runId: string): Promise<ScheduleRun> {
    return this.request<ScheduleRun>(`/scheduling/runs/${runId}`);
  }

  async getScheduleResults(runId: string): Promise<any> {
    return this.request(`/scheduling/runs/${runId}/results`);
  }

  async deleteScheduleRun(runId: string): Promise<void> {
    await this.request(`/scheduling/runs/${runId}`, {
      method: 'DELETE',
    });
  }

  // Progress API
  async getScheduleProgress(runId: string): Promise<ProgressStep[]> {
    return this.request<ProgressStep[]>(`/progress/runs/${runId}/progress`);
  }

  async getCurrentProgress(runId: string): Promise<any> {
    return this.request(`/progress/runs/${runId}/progress/current`);
  }

  async clearProgress(runId: string): Promise<void> {
    await this.request(`/progress/runs/${runId}/progress`, {
      method: 'DELETE',
    });
  }

  // Files API
  async uploadFile(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/files/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed! status: ${response.status}`);
    }

    return response.json();
  }

  async listFiles(): Promise<any> {
    return this.request('/files/list');
  }

  async downloadFile(filename: string): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/files/download/${filename}`);
    if (!response.ok) {
      throw new Error(`Download failed! status: ${response.status}`);
    }
    return response.blob();
  }
}

export const apiService = new ApiService();
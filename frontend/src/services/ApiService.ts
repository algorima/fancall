import { BaseApiService } from "@aioia/core";

/**
 * API Service for Fancall standalone app
 * No authentication required for public API access
 */
export class ApiService extends BaseApiService {
  constructor() {
    super(process.env.NEXT_PUBLIC_API_BASE_URL, "");
  }

  /**
   * No authentication headers for public API
   */
  protected getAuthHeaders(): Record<string, string> {
    return {
      "Content-Type": "application/json",
    };
  }

  /**
   * Handle API errors
   */
  protected async handleError(response: Response): Promise<never> {
    const errorData = (await response.json()) as { detail?: string };
    throw new Error(errorData.detail || `API Error: ${response.status}`);
  }
}

// Singleton instance
let apiServiceInstance: ApiService | null = null;

export const getApiService = (): ApiService => {
  if (!apiServiceInstance) {
    apiServiceInstance = new ApiService();
  }
  return apiServiceInstance;
};

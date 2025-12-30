import { BaseCrudRepository } from "@aioia/core";

import type {
  AgentDispatchRequest,
  DispatchResponse,
  LiveRoom,
  TokenResponse,
} from "../schemas";
import {
  dispatchResponseSchema,
  liveRoomSchema,
  tokenResponseSchema,
} from "../schemas";

export class LiveRoomRepository extends BaseCrudRepository<LiveRoom> {
  readonly resource = "live-rooms";

  protected getDataSchema() {
    return liveRoomSchema;
  }

  /**
   * Generate user access token for a live room
   * POST /live-rooms/{roomId}/token
   */
  async generateToken(
    roomId: string,
    fetchOptions?: RequestInit,
  ): Promise<TokenResponse> {
    const url = `${this.apiService.buildUrl(this.resource)}/${roomId}/token`;
    const rawResponse = await this.apiService.request(url, {
      ...fetchOptions,
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    return this.validateResponse(rawResponse, tokenResponseSchema);
  }

  /**
   * Dispatch agent to a live room (generic)
   * POST /live-rooms/{roomId}/dispatch
   */
  async dispatchAgent(
    roomId: string,
    request: AgentDispatchRequest,
    fetchOptions?: RequestInit,
  ): Promise<DispatchResponse> {
    const url = `${this.apiService.buildUrl(this.resource)}/${roomId}/dispatch`;
    const rawResponse = await this.apiService.request(url, {
      ...fetchOptions,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    return this.validateResponse(rawResponse, dispatchResponseSchema);
  }
}

import axios from 'axios';
import type { ObservationResponse, ApiError } from '../types';

const API_BASE_URL = 'http://localhost:8000';

export const api = {
  async testConnection(): Promise<any> {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/test-ebird`);
      return response.data;
    } catch (error) {
      console.error('Error testing eBird connection:', error);
      throw error;
    }
  },

  async getObservationsByLocation(
    location: string,
    daysBack: number = 7
  ): Promise<ObservationResponse | ApiError> {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/observations/by-location`, {
        params: {
          location,
          days_back: daysBack,
        },
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching observations:', error);
      throw error;
    }
  },
};

export interface Location {
  lat: number;
  lng: number;
}

export interface Species {
  count: number;
  scientific_name: string;
  last_seen: string;
}

export interface SpeciesMap {
  [speciesName: string]: Species;
}

export interface ObservationResponse {
  location: Location;
  total_observations: number;
  unique_species: number;
  species: SpeciesMap;
  days_searched: number;
}

export interface ApiError {
  error: string;
  message?: string;
  hint?: string;
}

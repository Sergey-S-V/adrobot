export interface Offer {
  id: number;
  name: string;
}
export interface OfferLink {
  id: string;
  keitaro_offer_id: number;
  name: string;
  state: string;
  share: number;
  pinned: boolean;
}
export interface Stream {
  id: string;
  keitaro_id: number;
  name: string;
  editable: boolean;
  dirty: boolean;
  offers: OfferLink[];
}
export interface Campaign {
  id: string;
  keitaro_id: number | null;
  name: string;
  streams: Stream[];
}
export interface Options {
  domains: Offer[];
  groups: Offer[];
  sources: Offer[];
}

import { useEffect, useId, useState } from "react";
import { api } from "./api";
import type { Offer } from "./types";

export function OfferPicker({
  label,
  selected,
  onSelect,
  onQuery,
}: {
  label: string;
  selected?: Offer;
  onSelect: (offer: Offer | undefined) => void;
  onQuery?: (query: string) => void;
}) {
  const id = useId();
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<Offer[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setRows([]);
    setError("");
    setLoading(true);
    const timer = setTimeout(() => {
      api<Offer[]>(
        `/offers/search?query=${encodeURIComponent(query)}`,
        undefined,
        "GET",
        controller.signal,
      )
        .then(setRows)
        .catch((err: Error) => {
          if (!controller.signal.aborted) setError(err.message);
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 250);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [query]);
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        role="combobox"
        aria-expanded={!selected}
        aria-controls={`${id}-results`}
        autoComplete="off"
        placeholder="Название или ID оффера"
        value={selected ? `${selected.name} (#${selected.id})` : query}
        onChange={(event) => {
          setQuery(event.target.value);
          setRows([]);
          onSelect(undefined);
          onQuery?.(event.target.value);
        }}
      />
      {!selected && (
        <>
          {loading && <small>Поиск в Keitaro…</small>}
          {error && <p role="alert">{error}</p>}
          <div
            id={`${id}-results`}
            className="suggestions"
            role="listbox"
            aria-label={label}
          >
            {rows.map((offer) => (
              <button
                type="button"
                role="option"
                aria-selected="false"
                key={offer.id}
                onClick={() => onSelect(offer)}
              >
                {offer.name} · #{offer.id}
              </button>
            ))}
          </div>
          {!loading && !error && rows.length === 0 && (
            <small>Офферы не найдены.</small>
          )}
        </>
      )}
    </div>
  );
}

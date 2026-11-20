import { useEffect, useState, type FormEvent } from "react";
import { api } from "./api";
import { OfferPicker } from "./OfferPicker";
import type { Campaign, Offer, Options, Stream } from "./types";

export default function App() {
  const [campaign, setCampaign] = useState<Campaign>();
  const [streamId, setStreamId] = useState("");
  const [creating, setCreating] = useState(false);
  const [options, setOptions] = useState<Options>();
  const [initialOffer, setInitialOffer] = useState<Offer>();
  const [offerQuery, setOfferQuery] = useState("");
  const [adding, setAdding] = useState(false);
  const [selectedOffer, setSelectedOffer] = useState<Offer>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const stream =
    campaign?.streams.find((row) => row.id === streamId) ??
    campaign?.streams.find((row) => row.editable) ??
    campaign?.streams[0];

  function open(value: Campaign) {
    setCampaign(value);
    setCreating(false);
    setAdding(false);
    window.location.hash = value.id;
  }
  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Не удалось выполнить запрос.",
      );
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    function load() {
      void run(async () => {
        setAdding(false);
        const id = window.location.hash.slice(1);
        if (id) setCampaign(await api<Campaign>(`/campaigns/${id}`));
        else {
          setCampaign(undefined);
        }
      });
    }
    load();
    window.addEventListener("hashchange", load);
    return () => window.removeEventListener("hashchange", load);
  }, []);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await run(async () =>
      open(
        await api<Campaign>("/campaigns", {
          name: form.get("name"),
          geo_codes: String(form.get("geo"))
            .split(/[\s,;]+/)
            .filter(Boolean),
          keitaro_offer_id: initialOffer?.id ?? Number(offerQuery),
          domain_keitaro_id: Number(form.get("domain")),
          group_keitaro_id: Number(form.get("group")),
          source_keitaro_id: Number(form.get("source")),
        }),
      ),
    );
  }
  async function fetchCampaign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const id = new FormData(event.currentTarget).get("campaign");
    await run(async () =>
      open(await api<Campaign>(`/campaigns/fetch/${id}`, {})),
    );
  }
  async function edit(path: string, body: unknown = {}, method = "POST") {
    await run(async () => {
      const result = await api<Stream>(path, body, method);
      setCampaign(
        (current) =>
          current && {
            ...current,
            streams: current.streams.map((row) =>
              row.id === result.id ? result : row,
            ),
          },
      );
      setAdding(false);
      setSelectedOffer(undefined);
    });
  }
  return (
    <main>
      <h1>Adrobot</h1>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <fieldset disabled={busy}>
        {!campaign && (
          <>
            <form onSubmit={fetchCampaign} className="row">
              <label>
                ID кампании Keitaro (необязательно){" "}
                <input
                  name="campaign"
                  aria-describedby="campaign-id-hint"
                  type="number"
                  min="1"
                  step="1"
                  required
                />
              </label>
              <button>Fetch Streams</button>
            </form>
            <p id="campaign-id-hint">
              <small>
                ID нужен только для загрузки существующей кампании. Для создания
                новой оставьте поле пустым и нажмите «Создать кампанию».
              </small>
            </p>
            <button
              onClick={() => {
                setCreating(!creating);
                if (!creating)
                  void run(async () =>
                    setOptions(await api<Options>("/creation-options")),
                  );
              }}
            >
              Создать кампанию
            </button>
          </>
        )}
        {creating && (
          <form onSubmit={create}>
            <h2>Новая кампания</h2>
            <label>
              Название кампании
              <input name="name" required maxLength={255} />
            </label>
            <label>
              GEO
              <input name="geo" required placeholder="AU" />
            </label>
            <OfferPicker
              label="Начальный оффер"
              selected={initialOffer}
              onSelect={setInitialOffer}
              onQuery={setOfferQuery}
            />
            <small>Выберите оффер или введите его числовой ID.</small>
            {options &&
              (
                [
                  ["domain", "Домен", options.domains],
                  ["group", "Группа", options.groups],
                  ["source", "Источник", options.sources],
                ] as const
              ).map(([name, label, rows]) => (
                <label key={name}>
                  {label}
                  <select
                    name={name}
                    aria-label={label}
                    required
                    defaultValue=""
                  >
                    <option value="" disabled>
                      Выберите
                    </option>
                    {rows.map((row) => (
                      <option value={row.id} key={row.id}>
                        {row.name}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            <button
              disabled={
                !options || (!initialOffer && !/^[1-9]\d*$/.test(offerQuery))
              }
            >
              Create
            </button>
          </form>
        )}
        {campaign && (
          <>
            <a href="#" onClick={() => setCreating(false)}>
              Назад
            </a>
            <h2>{campaign.name}</h2>
            <button
              disabled={!campaign.keitaro_id}
              onClick={() =>
                void run(async () =>
                  open(
                    await api<Campaign>(
                      `/campaigns/fetch/${campaign.keitaro_id}`,
                      {},
                    ),
                  ),
                )
              }
            >
              Fetch Streams
            </button>
            <div className="row">
              {campaign.streams.map((row) => (
                <button
                  key={row.id}
                  aria-pressed={stream?.id === row.id}
                  onClick={() => {
                    setStreamId(row.id);
                    setAdding(false);
                  }}
                >
                  {row.name}
                </button>
              ))}
            </div>
            {stream && (
              <section className={stream.dirty ? "draft" : ""}>
                <h3>{stream.name}</h3>
                {stream.editable && (
                  <>
                    <button
                      onClick={() => {
                        setAdding(!adding);
                        setSelectedOffer(undefined);
                      }}
                    >
                      Добавить оффер
                    </button>
                    {adding && (
                      <div className="add-offer">
                        <OfferPicker
                          label="Поиск оффера"
                          selected={selectedOffer}
                          onSelect={setSelectedOffer}
                        />
                        <button
                          disabled={!selectedOffer}
                          onClick={() =>
                            void edit(`/streams/${stream.id}/offers`, {
                              keitaro_offer_id: selectedOffer!.id,
                            })
                          }
                        >
                          Add
                        </button>
                        <button onClick={() => setAdding(false)}>
                          Закрыть
                        </button>
                      </div>
                    )}
                    <table>
                      <thead>
                        <tr>
                          <th>Оффер</th>
                          <th>ID</th>
                          <th>Доля</th>
                          <th>Pin</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {stream.offers.map((row) => (
                          <tr
                            key={row.id}
                            className={row.state === "removed" ? "removed" : ""}
                          >
                            <td>{row.name}</td>
                            <td>{row.keitaro_offer_id}</td>
                            <td>{row.share}%</td>
                            <td>
                              <input
                                type="checkbox"
                                aria-label={`Pin ${row.name}`}
                                checked={row.pinned}
                                disabled={row.state !== "active"}
                                onChange={(event) =>
                                  void edit(
                                    `/streams/${stream.id}/offers/${row.id}/pin`,
                                    { pinned: event.target.checked },
                                    "PUT",
                                  )
                                }
                              />
                            </td>
                            <td>
                              <button
                                onClick={() =>
                                  void edit(
                                    `/streams/${stream.id}/offers/${row.id}/${row.state === "removed" ? "restore" : "remove"}`,
                                  )
                                }
                              >
                                {row.state === "removed"
                                  ? "Bring Back"
                                  : "Remove"}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <button
                      disabled={!stream.dirty}
                      onClick={() => void edit(`/streams/${stream.id}/cancel`)}
                    >
                      Cancel
                    </button>
                    <button
                      disabled={!stream.dirty}
                      onClick={() => void edit(`/streams/${stream.id}/publish`)}
                    >
                      Push to KT
                    </button>
                  </>
                )}
              </section>
            )}
          </>
        )}
      </fieldset>
      {busy && <p role="status">Выполняется запрос…</p>}
    </main>
  );
}

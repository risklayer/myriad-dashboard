import { memoize, round } from "lodash";
import { components } from "../../data/types/api";
import type { Api as DataTableApi } from "datatables.net-bs5";

export function floatTo3Digits(value: number): string {
  if (value > 100) {
    return String(round(value, 0));
  }
  if (value > 10) {
    return String(round(value, 1));
  }
  if (value > 1) {
    return String(round(value, 2));
  }
  if (value > 0.1) {
    return String(round(value, 3));
  }
  if (value > 0.01) {
    return String(round(value, 4));
  }
  if (value > 0.001) {
    return String(round(value, 5));
  }
  if (value > 0.0001) {
    return String(round(value, 6));
  }

  if (value === 0) {
    return "0";
  }

  if (value == null) {
    return "-";
  }

  return value.toExponential(2);
}

export function slugify(str: string) {
  return str
    .normalize("NFKD")
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .trim()
    .replace(/[-\s]+/g, "-");
}

export function createGeoJSONDownload(
  data: {
    features: components["schemas"]["ShapeFeature"][];
    type: "FeatureCollection";
  },
  filename: string
) {
  let url;
  try {
    const mimeType = "application/geo+json";
    const blob = new Blob([JSON.stringify(data)], { type: mimeType });
    const anchor = document.createElement("a");
    url = (window.webkitURL || window.URL).createObjectURL(blob);

    anchor.download = filename;
    anchor.href = url;
    anchor.dataset.downloadurl = [mimeType, anchor.download, anchor.href].join(
      ":"
    );
    anchor.click();
  } catch (err) {
    console.error("Failed to download: ", err);
    toast("Error creating download");
  } finally {
    if (url) {
      window.URL.revokeObjectURL(url);
    }
  }
}

export const memoizeUnlessNull = ((func, resolver) => {
  const memoized = memoize(func, resolver);
  return (...args: Parameters<typeof func>) => {
    let result = null;
    try {
      result = memoized(...args);
    } finally {
      if (result === null) {
        // @ts-expect-error memoized.resolve is an undocumented method
        memoized.cache.delete(memoized.resolve(...args));
      }
    }
    return result;
  };
}) as typeof memoize;

export function createCiteButton(url: string) {
  return {
    text: "Cite",
    titleAttr: "See citation information for this data",
    attr: {
      "hx-get": url,
      "hx-target": "#modal-body",
      "hx-swap": "innerHTML",
      "data-bs-toggle": "modal",
      "data-bs-target": "#main-modal",
    },
    init: (dt: DataTableApi<any>, node: JQuery, config: any) =>
      window.htmx.process(node[0]),
  };
}

import { identity, memoize, sortBy } from "lodash";
import createClient from "openapi-fetch";
import {
  ApiPaths,
  DataTableColumnSchema,
  FeatureCollectionSchema,
  FeatureCollectionShapeFeature,
  FeatureCollectionUnionShapeFeatureShapeFeatureArbitraryProperties,
  HrscEventSchema,
  ShapeFeature,
  type CountriesEnum,
  type Nuts3AreaSchema,
  type paths,
} from "../../data/types/api";

// import "../../dashboard/js/scripts.d";

export const client = createClient<paths>();

export const getShapesList = memoize(
  async function getShapesList(
    countries: CountriesEnum | CountriesEnum[]
  ): Promise<ShapeFeature[] | null> {
    if (Array.isArray(countries)) {
      return (
        await Promise.all(countries.map((country) => getShapesList(country)))
      )
        .flat(1)
        .filter((val) => val != null);
    }
    const {
      data, // only present if 2XX response
      error, // only present if 4XX or 5XX response
    } = await client.GET(ApiPaths.data_v1_areas_shapes, {
      params: {
        query: { countries: [countries] },
      },
    });
    if (error) {
      window.toast("Sorry, there was a problem retrieving the area outlines.");
      console.error(error);
      return null;
    }
    const shapes = data.features;
    return shapes;
  },
  (countries: string | string[]) => sortBy([countries].flat(), identity).join()
);

export const getEventDetail = memoize(
  async function getEventDetail(
    ids: number | number[]
  ): Promise<HrscEventSchema[]> {
    if (Array.isArray(ids)) {
      return (await Promise.all(ids.map((id) => getEventDetail(id))))
        .flat(1)
        .filter((val) => val != null);
    }
    const {
      data, // only present if 2XX response
      error, // only present if 4XX or 5XX response
    } = await client.GET("/data/api/v1/hrsc/event/{id}/detail", {
      params: {
        path: { id: ids as number },
      },
    });
    if (error) {
      window.toast("Sorry, there was a problem retrieving the area outlines.");
      console.error(error);
      return [];
    }
    return [data].filter(Boolean);
  },
  (ids: number | number[]) => sortBy([ids].flat(), identity).join()
);
export const getAreasMap = memoize(
  async function getAreasMap(
    countries: CountriesEnum | CountriesEnum[],
    bbox?: string
  ): Promise<Record<string, Nuts3AreaSchema> | null> {
    if (Array.isArray(countries)) {
      return (
        await Promise.all(countries.map((country) => getAreasMap(country)))
      ).reduce((acc, areas) => ({ ...acc, ...areas }), {});
    }
    const {
      data, // only present if 2XX response
      error, // only present if 4XX or 5XX response
    } = await client.GET(ApiPaths.data_v1_areas_map, {
      params: {
        query: { countries: [countries], bbox },
      },
    });
    if (error) {
      window.toast("Sorry, there was a problem retrieving the area outlines.");
      console.error(error);
      return null;
    }
    return data;
  },
  (countries: string | string[], bbox?: string) =>
    [sortBy([countries].flat(), identity), bbox].flat().join()
);
export const getValuesMap = memoize(
  async function getValuesMap(
    countries: CountriesEnum[],
    columns: string[] | string
  ): Promise<Record<string, Record<string, number>> | null> {
    const {
      data, // only present if 2XX response
      error, // only present if 4XX or 5XX response
    } = await client.GET(ApiPaths.data_v1_values_values, {
      params: {
        query: { countries, columns: [columns].flat() },
      },
    });
    if (error) {
      window.toast("Sorry, there was a problem retrieving the data.");
      console.error(error);
      return null;
    }
    return data;
  },
  (countries: string[], columns: string[] | string) =>
    [sortBy([countries].flat(), identity), sortBy([columns].flat(), identity)]
      .flat()
      .join()
);

export async function downloadGeoJSON({
  countries,
  areas,
  columns,
}: {
  countries?: CountriesEnum[] | CountriesEnum;
  areas?: string[] | string;
  columns?: string[] | string;
}): Promise<FeatureCollectionSchema | null> {
  const {
    data, // only present if 2XX response
    error, // only present if 4XX or 5XX response
  } = await client.GET(ApiPaths.data_v1_areas_shapes, {
    params: {
      query: {
        countries: [countries!].flat().filter(Boolean),
        columns: [columns!].flat().filter(Boolean),
        nuts3areas: [areas!].flat().filter(Boolean),
      },
    },
  });
  if (error) {
    window.toast("Sorry, there was a problem retrieving dataset details.");
    console.error(error);
    return null;
  }
  return data;
}

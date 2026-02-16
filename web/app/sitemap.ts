import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: "https://commontrust.credit",
      lastModified: new Date()
    },
    {
      url: "https://commontrust.credit/reviews",
      lastModified: new Date()
    }
  ];
}


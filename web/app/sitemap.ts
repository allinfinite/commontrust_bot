import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: "https://trust.bigislandbulletin.com",
      lastModified: new Date()
    },
    {
      url: "https://trust.bigislandbulletin.com/reviews",
      lastModified: new Date()
    }
  ];
}


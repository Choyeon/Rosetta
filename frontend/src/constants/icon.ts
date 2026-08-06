import type { Favicon } from "@/types/config.ts";

export const defaultFavicons: Favicon[] = [
	{
		src: "/favicon/favicon.ico",
		sizes: "any",
		rel: "icon",
		type: "image/x-icon",
	},
	{
		src: "/favicon/favicon-light-32.png",
		theme: "light",
		sizes: "32x32",
		type: "image/png",
		rel: "icon",
	},
	{
		src: "/favicon/favicon-dark-32.png",
		theme: "dark",
		sizes: "32x32",
		type: "image/png",
		rel: "icon",
	},
	{
		src: "/favicon/favicon-light-128.png",
		theme: "light",
		sizes: "128x128",
		type: "image/png",
		rel: "icon",
	},
	{
		src: "/favicon/favicon-dark-128.png",
		theme: "dark",
		sizes: "128x128",
		type: "image/png",
		rel: "icon",
	},
	{
		src: "/favicon/favicon-light-180.png",
		theme: "light",
		sizes: "180x180",
		type: "image/png",
		rel: "apple-touch-icon",
	},
	{
		src: "/favicon/favicon-dark-180.png",
		theme: "dark",
		sizes: "180x180",
		type: "image/png",
		rel: "apple-touch-icon",
	},
	{
		src: "/favicon/favicon-light-192.png",
		theme: "light",
		sizes: "192x192",
		type: "image/png",
		rel: "icon",
	},
	{
		src: "/favicon/favicon-dark-192.png",
		theme: "dark",
		sizes: "192x192",
		type: "image/png",
		rel: "icon",
	},
];

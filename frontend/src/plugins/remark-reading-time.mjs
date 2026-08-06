// biome-ignore lint/suspicious/noShadowRestrictedNames: <toString from mdast-util-to-string>
import { toString } from "mdast-util-to-string";
import getReadingTime from "reading-time";

export function remarkReadingTime() {
	return (tree, { data }) => {
		const textOnPage = toString(tree);
		const readingTime = getReadingTime(textOnPage);
		const minutes = Math.max(1, Math.round(readingTime.minutes));
		const words = readingTime.words;

		if (data.astro?.frontmatter) {
			data.astro.frontmatter.minutes = minutes;
			data.astro.frontmatter.words = words;
		}

		data.readingTime = { minutes, words };
	};
}

export const DIRECTORY_PAGE_SIZE = 6;

export function directoryPage(players, page) {
  const pageCount = Math.max(1, Math.ceil(players.length / DIRECTORY_PAGE_SIZE));
  const currentPage = Math.max(1, Math.min(page, pageCount));
  const pageStart = (currentPage - 1) * DIRECTORY_PAGE_SIZE;
  return { pageCount, currentPage, pageStart,
    directory: players.slice(pageStart, pageStart + DIRECTORY_PAGE_SIZE) };
}

import "@testing-library/jest-dom/vitest";
import "fake-indexeddb/auto";

// jsdom lacks layout APIs used by the UI
if (!Element.prototype.scrollIntoView) Element.prototype.scrollIntoView = () => {};

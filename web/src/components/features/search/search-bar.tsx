import { MagnifyingGlass, Microphone } from "@phosphor-icons/react/dist/ssr";

import { SearchField } from "./search-field";

/** Search a pro or a look, by typing or by voice. Icons are drawn on the server. */
export function SearchBar({ defaultValue = "" }: { defaultValue?: string }) {
  return (
    <SearchField
      defaultValue={defaultValue}
      icons={{
        search: <MagnifyingGlass size={24} weight="bold" />,
        mic: <Microphone aria-hidden size={22} weight="duotone" />,
        micOn: <Microphone aria-hidden size={22} weight="fill" />,
      }}
    />
  );
}

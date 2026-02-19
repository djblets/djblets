export { List as ConfigFormsList } from './models/listModel';
export { ListItem as ConfigFormsListItem } from './models/listItemModel';
export { ListItemView as ConfigFormsListItemView } from './views/listItemView';
export {
    ListItems as ConfigFormsListItems,
} from './collections/listItemsCollection';
export { ListView as ConfigFormsListView } from './views/listView';
export { PagesView as ConfigFormsPagesView } from './views/pagesView';
export {
    TableItemView as ConfigFormsTableItemView,
} from './views/tableItemView';
export { TableView as ConfigFormsTableView } from './views/tableView';


/*
 * We also define a legacy namespace for Djblets.Config.
 *
 * This doesn't play nicely with TypeScript-based code, so the above names are
 * preferable. The Djblets.Config.* names should be considered deprecated and
 * may be removed in a future release.
 */

import { List } from './models/listModel';
import { ListItem } from './models/listItemModel';
import { ListItemView } from './views/listItemView';
import { ListItems } from './collections/listItemsCollection';
import { ListView } from './views/listView';
import { PagesView } from './views/pagesView';
import { TableItemView } from './views/tableItemView';
import { TableView } from './views/tableView';

export const Config = {
    List,
    ListItem,
    ListItemView,
    ListItems,
    ListView,
    PagesView,
    TableItemView,
    TableView,
};

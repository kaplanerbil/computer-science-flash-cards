drop table if exists cards;
create table cards (
  id integer primary key autoincrement,
  type tinyint not null, /* 1 for vocab, 2 for code */
  front text not null,
  back text not null,
  imageBase64Back blob,
  imageBase64Front blob,
  known boolean default 0
);

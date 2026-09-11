import types
from uuid import uuid4
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi_pagination import LimitOffsetPage, LimitOffsetParams
from sqlalchemy import ForeignKey, String, select
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from app.core.database.base import table_registry
from app.core.pagination.schemas import CustomLimitOffsetPage
from app.core.repository import BaseRepository
from app.models.pokemon import Pokemon
from app.shared.schemas import FilterPage


@table_registry.mapped_as_dataclass
class PokedexTest:
    __tablename__ = "pokedex_test"

    trainer_id: Mapped[str] = mapped_column(String, nullable=False)
    pokemon_id: Mapped[str] = mapped_column(ForeignKey("pokemons.id"), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    pokemon: Mapped[Pokemon] = relationship("Pokemon", init=False)
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default_factory=lambda: str(uuid4()), init=False
    )


class PokemonBaseRepository(BaseRepository[Pokemon]):
    model = Pokemon
    relations = (selectinload(Pokemon.moves),)
    default_order_by = "order"


class PokedexBaseRepository(BaseRepository[PokedexTest]):
    model = PokedexTest


class TestBaseRepositoryApplyOrderBy:
    @staticmethod
    def test_apply_order_by_returns_same_query_when_order_by_is_none():
        repository = PokedexBaseRepository(session=AsyncMock())
        query = select(PokedexTest)
        page_filter = FilterPage()

        result_query = repository._apply_order_by(query, page_filter)

        assert result_query is query
        assert "ORDER BY" not in str(result_query)

    @staticmethod
    def test_apply_order_by_returns_same_query_when_order_path_is_blank():
        repository = PokemonBaseRepository(session=AsyncMock())
        query = select(Pokemon)
        page_filter = FilterPage.build(order_by="   ")

        result_query = repository._apply_order_by(query, page_filter)

        assert result_query is query
        assert "ORDER BY" not in str(result_query)

    @staticmethod
    def test_apply_order_by_uses_default_order_by_when_page_filter_is_none():
        repository = PokemonBaseRepository(session=AsyncMock())
        query = select(Pokemon)

        result_query = repository._apply_order_by(query)

        assert 'ORDER BY pokemons."order"' in str(result_query)

    @staticmethod
    def test_apply_order_by_uses_page_filter_order_by_when_provided():
        repository = PokemonBaseRepository(session=AsyncMock())
        query = select(Pokemon)
        page_filter = FilterPage.build(order_by="name")

        result_query = repository._apply_order_by(query, page_filter)

        assert "ORDER BY pokemons.name" in str(result_query)

    @staticmethod
    def test_apply_order_by_applies_outer_join_for_relationship_path():
        repository = PokedexBaseRepository(session=AsyncMock())
        query = select(PokedexTest)
        page_filter = FilterPage.build(order_by="pokemon.order")

        result_query = repository._apply_order_by(query, page_filter)
        result_query_str = str(result_query)

        assert "LEFT OUTER JOIN pokemons" in result_query_str
        assert 'ORDER BY pokemons."order"' in result_query_str

    @staticmethod
    def test_apply_order_by_raises_error_when_relation_is_invalid():
        repository = PokedexBaseRepository(session=AsyncMock())
        query = select(PokedexTest)
        page_filter = FilterPage.build(order_by="invalid.order")

        with pytest.raises(ValueError, match="Invalid default_order_by relation"):
            repository._apply_order_by(query, page_filter)

    @staticmethod
    def test_apply_order_by_raises_error_for_collection_relationship():
        repository = PokemonBaseRepository(session=AsyncMock())
        query = select(Pokemon)
        page_filter = FilterPage.build(order_by="moves.name")

        with pytest.raises(
            ValueError, match="collection relationships are not supported"
        ):
            repository._apply_order_by(query, page_filter)

    @staticmethod
    def test_apply_order_by_raises_error_when_path_token_is_not_relationship():
        repository = PokemonBaseRepository(session=AsyncMock())
        query = select(Pokemon)
        page_filter = FilterPage.build(order_by="order.name")

        with pytest.raises(ValueError, match="is not a relationship"):
            repository._apply_order_by(query, page_filter)

    @staticmethod
    def test_apply_order_by_raises_error_when_last_field_is_invalid():
        repository = PokedexBaseRepository(session=AsyncMock())
        query = select(PokedexTest)
        page_filter = FilterPage.build(order_by="pokemon.invalid_field")

        with pytest.raises(ValueError, match="Invalid default_order_by field"):
            repository._apply_order_by(query, page_filter)

    @staticmethod
    def test_apply_order_by_raises_error_when_last_token_is_not_column():
        repository = PokedexBaseRepository(session=AsyncMock())
        query = select(PokedexTest)
        page_filter = FilterPage.build(order_by="pokemon.moves")

        with pytest.raises(ValueError, match="last token must be a mapped column"):
            repository._apply_order_by(query, page_filter)


class TestBaseRepositoryRelationHelpers:
    @staticmethod
    def test_extract_relations_filters_extracts_and_mutates_raw_filters():
        raw_filters = {
            "pokemon_name": "pikachu",
            "type": "fire",
            "pokemon_": "ignored",
            "trainer_id": "trainer-id",
            "pokemon_order": None,
        }

        result = BaseRepository._extract_relations_filters(
            raw_filters, relation="pokemon"
        )

        assert result == {
            "name": "pikachu",
        }
        assert "pokemon_name" not in raw_filters
        assert raw_filters["type"] == "fire"
        assert "trainer_id" in raw_filters
        assert "pokemon_" in raw_filters

    @staticmethod
    def test_build_name_predicate_returns_none_when_attr_has_no_mapper():
        predicate = BaseRepository._build_name_predicate(
            Pokemon.name,
            Pokemon.name.property,
            "pikachu",
        )

        assert predicate is None

    @staticmethod
    def test_build_name_predicate_builds_any_for_uselist_relationship():
        predicate = BaseRepository._build_name_predicate(
            Pokemon.types,
            Pokemon.types.property,
            "fire",
        )

        predicate_sql = str(predicate)
        assert predicate is not None
        assert ".name" in predicate_sql

    @staticmethod
    def test_build_name_predicate_builds_has_for_scalar_relationship():
        predicate = BaseRepository._build_name_predicate(
            PokedexTest.pokemon,
            PokedexTest.pokemon.property,
            "pikachu",
        )

        predicate_sql = str(predicate)
        assert predicate is not None
        assert "pokemons.name" in predicate_sql

    @staticmethod
    def test_build_name_predicate_returns_none_when_related_model_has_no_name_attr():
        related_model = types.SimpleNamespace()
        model_property = types.SimpleNamespace(
            mapper=types.SimpleNamespace(class_=related_model),
            uselist=False,
        )

        predicate = BaseRepository._build_name_predicate(
            model_attr=Mock(),
            model_property=model_property,
            value="pikachu",
        )

        assert predicate is None

    @staticmethod
    def test_build_single_token_predicate_delegates_to_build_name_predicate():
        repository = PokemonBaseRepository(session=AsyncMock())

        with patch.object(
            repository,
            "_build_name_predicate",
            return_value="delegated-predicate",
        ) as build_name_predicate_mock:
            result = repository._build_single_token_predicate(
                Pokemon.types,
                Pokemon.types.property,
                "fire",
            )

        assert result == "delegated-predicate"
        build_name_predicate_mock.assert_called_once_with(
            Pokemon.types,
            Pokemon.types.property,
            "fire",
        )

    @staticmethod
    def test_build_nested_predicate_returns_none_when_property_is_not_relationship():
        repository = PokemonBaseRepository(session=AsyncMock())

        predicate = repository._build_nested_predicate(
            Pokemon.name,
            Pokemon.name.property,
            ["name", "id"],
            "pikachu",
        )

        assert predicate is None

    @staticmethod
    def test_build_nested_predicate_builds_predicate_for_relationship_path():
        repository = PokemonBaseRepository(session=AsyncMock())

        predicate = repository._build_nested_predicate(
            Pokemon.types,
            Pokemon.types.property,
            ["types", "name"],
            "fire",
        )

        predicate_sql = str(predicate)
        assert predicate is not None
        assert ".name" in predicate_sql

    @staticmethod
    def test_build_nested_predicate_returns_none_when_nested_predicate_is_none():
        repository = PokedexBaseRepository(session=AsyncMock())

        with patch.object(repository, "_build_relation_predicate", return_value=None):
            predicate = repository._build_nested_predicate(
                PokedexTest.pokemon,
                PokedexTest.pokemon.property,
                ["pokemon", "name"],
                "pikachu",
            )

        assert predicate is None

    @staticmethod
    def test_build_nested_predicate_builds_has_for_scalar_relationship():
        repository = PokedexBaseRepository(session=AsyncMock())
        nested_predicate = Pokemon.name == "pikachu"

        with patch.object(
            repository,
            "_build_relation_predicate",
            return_value=nested_predicate,
        ):
            predicate = repository._build_nested_predicate(
                PokedexTest.pokemon,
                PokedexTest.pokemon.property,
                ["pokemon", "name"],
                "pikachu",
            )

        assert predicate is not None
        assert "pokemons.name" in str(predicate)

    @staticmethod
    def test_build_relation_predicate_handles_empty_path():
        repository = PokemonBaseRepository(session=AsyncMock())

        predicate = repository._build_relation_predicate(Pokemon, [], "fire")

        assert predicate is None

    @staticmethod
    def test_build_relation_predicate_returns_none_for_invalid_attr():
        repository = PokemonBaseRepository(session=AsyncMock())

        predicate = repository._build_relation_predicate(
            Pokemon, ["not_exists"], "fire"
        )

        assert predicate is None

    @staticmethod
    def test_build_relation_predicate_builds_column_predicate_for_single_token():
        repository = PokemonBaseRepository(session=AsyncMock())

        predicate = repository._build_relation_predicate(Pokemon, ["name"], "pikachu")

        assert predicate is not None
        assert "pokemons.name" in str(predicate)

    @staticmethod
    def test_build_relation_predicate_builds_nested_relationship_predicate():
        repository = PokemonBaseRepository(session=AsyncMock())

        predicate = repository._build_relation_predicate(
            Pokemon, ["types", "name"], "fire"
        )

        assert predicate is not None
        assert ".name" in str(predicate)

    @staticmethod
    def test_apply_relations_filters_returns_query_when_relation_attr_not_found():
        repository = PokedexBaseRepository(session=AsyncMock())
        query = select(PokedexTest)

        result_query = repository._apply_relations_filters(
            query,
            relations_filters={"name": "pikachu"},
            relation="not_exists",
        )

        assert result_query is query

    @staticmethod
    def test_apply_relations_filters_returns_query_when_relation_has_no_mapper():
        repository = PokedexBaseRepository(session=AsyncMock())
        query = select(PokedexTest)

        result_query = repository._apply_relations_filters(
            query,
            relations_filters={"name": "pikachu"},
            relation="nickname",
        )

        assert result_query is query

    @staticmethod
    def test_apply_relations_filters_skips_none_values_and_returns_same_query():
        repository = PokedexBaseRepository(session=AsyncMock())
        query = select(PokedexTest)

        result_query = repository._apply_relations_filters(
            query,
            relations_filters={"name": None},
            relation="pokemon",
        )

        assert result_query is query

    @staticmethod
    def test_apply_relations_filters_uses_valid_column_fallback_when_predicate_is_none():
        repository = PokedexBaseRepository(session=AsyncMock())
        query = select(PokedexTest)

        with patch.object(repository, "_build_relation_predicate", return_value=None):
            result_query = repository._apply_relations_filters(
                query,
                relations_filters={"name": "pikachu"},
                relation="pokemon",
            )

        assert result_query is not query
        assert "pokemons.name" in str(result_query)

    @staticmethod
    def test_apply_relations_filters_returns_same_query_when_no_predicates_generated():
        repository = PokedexBaseRepository(session=AsyncMock())
        query = select(PokedexTest)

        result_query = repository._apply_relations_filters(
            query,
            relations_filters={"not_a_column": "value"},
            relation="pokemon",
        )

        assert result_query is query

    @staticmethod
    def test_apply_relations_filters_uses_any_for_uselist_relation():
        repository = PokemonBaseRepository(session=AsyncMock())
        query = select(Pokemon)

        result_query = repository._apply_relations_filters(
            query,
            relations_filters={"name": "fire"},
            relation="types",
        )

        assert result_query is not query
        assert ".name" in str(result_query)


class TestBaseRepositoryTotal:
    @staticmethod
    @pytest.mark.asyncio
    async def test_total_returns_count_from_scalar():
        expected_total = 10
        mock_session = AsyncMock()
        mock_session.scalar = AsyncMock(return_value=expected_total)

        repository = PokemonBaseRepository(session=mock_session)
        result = await repository.total()

        assert result == expected_total
        mock_session.scalar.assert_awaited_once()

    @staticmethod
    @pytest.mark.asyncio
    async def test_total_returns_zero_when_scalar_is_none():
        mock_session = AsyncMock()
        mock_session.scalar = AsyncMock(return_value=None)

        repository = PokemonBaseRepository(session=mock_session)
        result = await repository.total()

        assert result == 0
        mock_session.scalar.assert_awaited_once()


class TestBaseRepositoryPersist:
    @staticmethod
    @pytest.mark.asyncio
    async def test_save_adds_commits_and_refreshes_entity():
        entity = object()
        mock_session = AsyncMock()

        repository = PokemonBaseRepository(session=mock_session)
        result = await repository.save(entity)

        assert result is entity
        mock_session.add.assert_called_once_with(entity)
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(entity)

    @staticmethod
    @pytest.mark.asyncio
    async def test_update_merges_commits_and_refreshes_entity():
        entity = object()
        merged_entity = object()
        mock_session = AsyncMock()
        mock_session.merge = AsyncMock(return_value=merged_entity)

        repository = PokemonBaseRepository(session=mock_session)
        result = await repository.update(entity)

        assert result is merged_entity
        mock_session.merge.assert_awaited_once_with(entity)
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(merged_entity)


class TestBaseRepositoryListAll:
    @staticmethod
    @pytest.mark.asyncio
    async def test_list_all_returns_all_items_when_not_paginated():
        expected_items = ["pikachu", "charizard"]
        scalars_result = Mock()
        scalars_result.all.return_value = expected_items

        mock_session = AsyncMock()
        mock_session.scalars = AsyncMock(return_value=scalars_result)

        repository = PokemonBaseRepository(session=mock_session)

        with patch("app.core.repository.base.is_paginate", return_value=False):
            result = await repository.list_all()

        assert result == expected_items
        mock_session.scalars.assert_awaited_once()

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_all_uses_paginate_when_page_filter_is_valid():
        result_limit = 50
        params = LimitOffsetParams(
            limit=1,
            offset=0,
        )
        expected_page = LimitOffsetPage.create(
            items=["pikachu"], total=1, params=params
        )
        mock_session = AsyncMock()
        repository = PokemonBaseRepository(session=mock_session)
        page_filter = FilterPage(offset=0, limit=50)

        with (
            patch("app.core.repository.base.is_paginate", return_value=True),
            patch(
                "app.core.repository.base.get_limit_offset_params",
                return_value=LimitOffsetParams(limit=50, offset=0),
            ),
            patch(
                "app.core.repository.base.paginate", new_callable=AsyncMock
            ) as paginate_mock,
        ):
            paginate_mock.return_value = expected_page
            result = await repository.list_all(page_filter=page_filter)

        assert len(result.items) == 1
        mock_session.scalars.assert_not_called()
        paginate_mock.assert_awaited_once()

        called_session, called_query = paginate_mock.call_args.args[:2]
        called_params = paginate_mock.call_args.kwargs["params"]

        assert called_session is mock_session
        assert called_query is not None
        assert called_params.limit == result_limit
        assert called_params.offset == 0

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_all_returns_custom_paginate_directly_when_paginate_already_matches():
        params = LimitOffsetParams(limit=50, offset=0)
        expected_page = CustomLimitOffsetPage.create(
            items=["pikachu"],
            total=1,
            params=params,
        )
        mock_session = AsyncMock()
        repository = PokemonBaseRepository(session=mock_session)
        page_filter = FilterPage(offset=0, limit=50)

        with (
            patch("app.core.repository.base.is_paginate", return_value=True),
            patch(
                "app.core.repository.base.get_limit_offset_params",
                return_value=params,
            ),
            patch(
                "app.core.repository.base.paginate", new_callable=AsyncMock
            ) as paginate_mock,
        ):
            paginate_mock.return_value = expected_page
            result = await repository.list_all(page_filter=page_filter)

        assert result is expected_page

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_all_uses_paginate_meta_total_when_total_attr_is_missing():
        params = LimitOffsetParams(limit=50, offset=0)
        paginate_result = types.SimpleNamespace(
            items=["pikachu"],
            meta=types.SimpleNamespace(total=1),
        )
        mock_session = AsyncMock()
        repository = PokemonBaseRepository(session=mock_session)
        page_filter = FilterPage(offset=0, limit=50)

        with (
            patch("app.core.repository.base.is_paginate", return_value=True),
            patch(
                "app.core.repository.base.get_limit_offset_params",
                return_value=params,
            ),
            patch(
                "app.core.repository.base.paginate", new_callable=AsyncMock
            ) as paginate_mock,
        ):
            paginate_mock.return_value = paginate_result
            result = await repository.list_all(page_filter=page_filter)

        assert result.items == ["pikachu"]
        assert result.meta.total == 1

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_all_applies_filter_by_from_page_filter():
        expected_items = ["pikachu"]
        scalars_result = Mock()
        scalars_result.all.return_value = expected_items

        mock_session = AsyncMock()
        mock_session.scalars = AsyncMock(return_value=scalars_result)

        repository = PokemonBaseRepository(session=mock_session)

        with patch("app.core.repository.base.is_paginate", return_value=False):
            result = await repository.list_all(
                page_filter=FilterPage.build(name="pikachu")
            )

        query = mock_session.scalars.await_args.args[0]

        assert result == expected_items
        assert "pokemons.name" in str(query)

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_all_applies_model_filter_with_relational_order_by():
        expected_items = ["pokedex-item"]
        scalars_result = Mock()
        scalars_result.all.return_value = expected_items

        mock_session = AsyncMock()
        mock_session.scalars = AsyncMock(return_value=scalars_result)

        repository = PokedexBaseRepository(session=mock_session)
        repository.default_order_by = "pokemon.order"

        with patch("app.core.repository.base.is_paginate", return_value=False):
            result = await repository.list_all(
                page_filter=FilterPage.build(trainer_id="trainer-id")
            )

        query = mock_session.scalars.await_args.args[0]

        assert result == expected_items
        assert "pokedex_test.trainer_id" in str(query)
        assert 'pokemons."order"' in str(query)

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_all_applies_pokemon_type_relation_filter():
        expected_items = ["pokedex-item"]
        scalars_result = Mock()
        scalars_result.all.return_value = expected_items

        mock_session = AsyncMock()
        mock_session.scalars = AsyncMock(return_value=scalars_result)

        repository = PokedexBaseRepository(session=mock_session)

        with patch("app.core.repository.base.is_paginate", return_value=False):
            result = await repository.list_all(
                page_filter=FilterPage.build(pokemon_type="fire")
            )

        query = mock_session.scalars.await_args.args[0]
        query_str = str(query)

        assert result == expected_items
        assert ".name" in query_str

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_all_uses_manual_paginate_path_when_relations_filter_exists():
        expected_items = ["pikachu"]
        scalars_result = Mock()
        scalars_result.all.return_value = expected_items

        mock_session = AsyncMock()
        mock_session.scalar = AsyncMock(return_value=1)
        mock_session.scalars = AsyncMock(return_value=scalars_result)

        repository = PokemonBaseRepository(session=mock_session)
        page_filter = FilterPage.build(pokemon_name="pikachu", offset=0, limit=10)

        with (
            patch("app.core.repository.base.is_paginate", return_value=True),
            patch(
                "app.core.repository.base.get_limit_offset_params",
                return_value=LimitOffsetParams(limit=10, offset=0),
            ),
            patch(
                "app.core.repository.base.paginate",
                new_callable=AsyncMock,
            ) as paginate_mock,
        ):
            result = await repository.list_all(page_filter=page_filter)

        assert result.items == expected_items
        mock_session.scalar.assert_awaited_once()
        mock_session.scalars.assert_awaited_once()
        paginate_mock.assert_not_awaited()


class TestBaseRepositoryFindBy:
    @staticmethod
    @pytest.mark.asyncio
    async def test_find_by_calls_filter_by_with_kwargs_and_returns_scalar_result():
        expected_entity = types.SimpleNamespace(name="pikachu")
        mock_session = AsyncMock()
        mock_session.scalar = AsyncMock(return_value=expected_entity)

        repository = PokemonBaseRepository(session=mock_session)
        result = await repository.find_by(name="pikachu", order=25)

        assert result == expected_entity
        mock_session.scalar.assert_awaited_once()

    @staticmethod
    @pytest.mark.asyncio
    async def test_find_by_returns_none_when_no_valid_filters_are_provided():
        mock_session = AsyncMock()
        repository = PokemonBaseRepository(session=mock_session)

        result = await repository.find_by(name=None, order=None)

        assert result is None
        mock_session.scalar.assert_not_called()

    @staticmethod
    @pytest.mark.asyncio
    async def test_find_by_aply_special_pokemon_name_filter_when_model_has_pokemon_relation():
        expected_entity = types.SimpleNamespace(id="pokedex-id")
        mock_session = AsyncMock()
        mock_session.scalar = AsyncMock(return_value=expected_entity)

        repository = PokedexBaseRepository(session=mock_session)

        result = await repository.find_by(
            trainer_id="trainer-id", pokemon_name="pikachu"
        )
        query = mock_session.scalar.await_args.args[0]

        assert result == expected_entity
        assert "pokemons.name" in str(query)
        assert "pokedex_test.trainer_id" in str(query)

    @staticmethod
    @pytest.mark.asyncio
    async def test_find_by_returns_none_when_one_of_filters_no_valid():
        mock_session = AsyncMock()
        expected_entity = types.SimpleNamespace(name="pikachu")
        mock_session.scalar = AsyncMock(return_value=expected_entity)
        repository = PokedexBaseRepository(session=mock_session)

        result = await repository.find_by(trainer_id=uuid4(), name="bulbasaur")

        assert result is None
        mock_session.scalar.assert_not_called()

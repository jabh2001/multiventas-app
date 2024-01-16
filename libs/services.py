
# Crear un alias para la tabla streaming_account para la subconsulta eti
sa_1 = db.aliased(StreamingAccount)

# Subconsulta eti: cuenta la cantidad de pantallas sin cliente para cada cuenta de streaming
screen_count_subquery = (
    db.session.query(
        Screen.account_id,
        db.func.count(Screen.id).label('screens_count')
    )
    .filter(Screen.client_id.is_(None))
    .group_by(Screen.account_id)
    .subquery()
)

# Subconsulta max_screens: obtén la cantidad máxima de pantallas sin cliente por plataforma
max_screens_subquery = (
    db.session.query(
        sa_1.platform_id,
        db.func.max(screen_count_subquery.c.screens_count).label('max_screens_count')
    )
    .join(screen_count_subquery, sa_1.id == screen_count_subquery.c.account_id)
    .group_by(sa_1.platform_id)
    .subquery()
)

# Consulta principal
results = (
    db.session.query(
        Platform,
        StreamingAccount,
        screen_count_subquery.c.screens_count
    )
    .join(StreamingAccount, StreamingAccount.platform_id == Platform.id)
    .join(screen_count_subquery, StreamingAccount.id == screen_count_subquery.c.account_id)
    .join(
        max_screens_subquery,
        db.and_(
            StreamingAccount.platform_id == max_screens_subquery.c.platform_id,
            screen_count_subquery.c.screens_count == max_screens_subquery.c.max_screens_count
        )
    )
    .order_by(Platform.id)
    .all()
)

# Iterar a través de los resultados
for platform, streaming_account, screens_count in results:
    # Procesar los resultados como desees
    print(f"Platform: {platform}, StreamingAccount: {streaming_account}, Screens Count: {screens_count}")


sql = """
SELECT
    platform.*,
    streaming_account.*,
    eti.screens_count
FROM
    platform
JOIN
    streaming_account ON streaming_account.platform_id = platform.id
JOIN (
    SELECT
        account_id,
        COUNT(id) AS screens_count
    FROM
        screen
    WHERE
        client_id IS NULL
    GROUP BY
        account_id
) eti ON streaming_account.id = eti.account_id
JOIN (
    SELECT
        platform_id,
        MAX(screens_count) AS max_screens_count
    FROM (
        SELECT
            sa.platform_id,
            COUNT(s.id) AS screens_count
        FROM
            streaming_account sa
        LEFT JOIN
            screen s ON s.account_id = sa.id AND s.client_id IS NULL
        GROUP BY
            sa.platform_id, sa.id
    ) screens_counts_per_account
    GROUP BY
        platform_id
) max_screens ON streaming_account.platform_id = max_screens.platform_id AND eti.screens_count = max_screens.max_screens_count
ORDER BY
    platform.id;
"""
